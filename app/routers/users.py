"""
用户路由模块
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.tasks import send_welcome_email, safe_delay
from app.database import get_db
from app.models import User
from app.auth import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token, token_hash
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.core.cache import redis_client
from app.core.limiter import limiter

import logging
import time

router = APIRouter(tags=["用户"])

logger = logging.getLogger(__name__)

# ========== 登录防爆破 ==========
LOGIN_MAX_FAILS = 5         # 最大登录失败次数
LOGIN_LOCK_SECONDS = 600    # 锁定时长: 10分钟

# 进程内降级存储 (Redis不可用时兜底; 多进程部署下不共享)
_local_locks: dict = {} # username -> 锁定截止时间戳
_local_fails: dict = {} # username -> (失败次数, 首次失败时间戳)

def _login_fail_key(username: str) -> str:
    return f"login:fail:{username}"

def _login_lock_key(username: str) -> str:
    return f"login:lock:{username}"

def _check_login_locked(username: str) -> bool:
    """检查账号是否被锁定 (Redis异常时查进程内兜底, 防止锁定被绕过)"""
    try:
        return redis_client.get(_login_lock_key(username)) is not None
    except Exception as e:
        logger.warning(f"登录锁定检查失败(Redis异常), 使用进程内兜底: {e}")
        deadline = _local_locks.get(username)
        if deadline is None:
            return False
        if time.time() < deadline:
            return True
        del _local_locks[username]  # 锁定已过期, 清除
        return False

def _record_login_fail(username: str):
    """记录登录失败, 连续失败5次锁定10分钟 (Redis异常时写入进程内兜底)"""
    try:
        now = time.time()
        fail_key = _login_fail_key(username)
        fails = redis_client.incr(fail_key)
        if fails == 1:
            redis_client.expire(fail_key, LOGIN_LOCK_SECONDS)
        if fails >= LOGIN_MAX_FAILS:
            redis_client.setex(_login_lock_key(username), LOGIN_LOCK_SECONDS, "1")
            _local_locks[username] = now + LOGIN_LOCK_SECONDS
            redis_client.delete(fail_key)
            logger.warning(f"用户 {username} 连续登录失败{LOGIN_MAX_FAILS}次, 账号锁定10分钟")
    except Exception as e:
        logger.warning(f"登录失败计数异常(Redis异常), 使用进程内兜底: {e}")
        now = time.time()
        fails, first_at = _local_fails.get(username, (0, now))
        if now - first_at > LOGIN_LOCK_SECONDS: # 计数窗口过期, 重新计
            fails, first_at = 0, now
        fails += 1
        if fails >= LOGIN_MAX_FAILS:
            _local_locks[username] = now + LOGIN_LOCK_SECONDS
            _local_fails.pop(username, None)
            logger.warning(f"用户 {username} 连续登录失败{LOGIN_MAX_FAILS}次, 账号锁定10分钟(进程内)")
        else:
            _local_fails[username] = (fails, first_at)

def _clear_login_fail(username: str):
    """登录成功后清除失败计数 (进程内和Redis都清)"""
    _local_fails.pop(username, None)
    try:
        redis_client.delete(_login_fail_key(username))
    except Exception:
        pass

# ========== Pydantic 模型 ==========

from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re

class UserUpdate(BaseModel):
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")

class UserProfile(BaseModel):
    id: int
    username: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if re.search(r'[\u4e00-\u9fff]', v):
            raise ValueError("密码不能包含中文字符")
        byte_length = len(v.encode('utf-8'))
        if byte_length > 72:
            raise ValueError("密码字节长度不能超过72字节")
        return v


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


# ========== 路由 ==========

@router.post("/token")
def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """OAuth2标准登录"""
    # 放爆破: 锁定中的账号直接拒绝
    if _check_login_locked(form_data.username):
        raise HTTPException(status_code=429, detail="登录失败次数过多, 账号已锁定10分钟")

    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        _record_login_fail(form_data.username)
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_login_fail(form_data.username)
    access_token = create_access_token(data={"sub": user.username, "type": "access"})
    refresh_token = create_refresh_token(data={"sub": user.username, "type": "refresh"})
    try:
        refresh_token_key = token_hash(refresh_token)
        redis_client.setex(f"refresh_token:{refresh_token_key}", settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60, "1")
    except Exception as e:
        logger.warning(f"刷新令牌存储失败(Redis异常, 已跳过): {e}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/token/refresh")
@limiter.limit("100/minute")
def refresh_token(
        request: Request,
        auth_token: str = Header(..., description="Bearer + 刷新令牌, 例如: Bearer eyJhbG..."),
        db: Session = Depends(get_db)
):
    """使用刷新令牌获取新访问令牌"""
    token = auth_token.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="刷新令牌为空")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="刷新令牌无效, 请重新登录")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误, 请重新登录")
    user = db.query(User).filter(User.username == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="刷新令牌无效, 请重新登录")
    try:
        token_key = token_hash(token)
        old_value = redis_client.set(f"refresh_token:{token_key}", "used", ex=10, get=True)
    except Exception as e:
        logger.warning(f"刷新令牌获取失败(Redis异常, 已跳过): {e}")
        raise HTTPException(status_code=500, detail="服务器错误, 请重新登录")
    if old_value != "1":
        raise HTTPException(status_code=401, detail="刷新令牌无效, 请重新登录")

    access_token = create_access_token(data={"sub": payload["sub"], "type": "access"})
    new_refresh_token = create_refresh_token(data={"sub": payload["sub"], "type": "refresh"})

    try:
        new_refresh_token_key = token_hash(new_refresh_token)
        redis_client.setex(f"refresh_token:{new_refresh_token_key}", settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60, "1")
    except Exception as e:
        logger.warning(f"刷新令牌存储失败: {e}")
        raise HTTPException(status_code=500, detail="服务器错误, 请重新登录")

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册"""
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # 异步发送欢迎邮件 (非核心路径, Celery/Redis不可用时降级, 不影响注册)
    safe_delay(send_welcome_email, db_user.username)

    return db_user


@router.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    """用户登录（JSON格式）"""
    # 放爆破: 锁定中的账号直接拒绝
    if _check_login_locked(user.username):
        raise HTTPException(status_code=429, detail="登录失败次数过多, 账号已锁定10分钟")
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        _record_login_fail(user.username)
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    _clear_login_fail(user.username)
    access_token = create_access_token(data={"sub": db_user.username, "type": "access"})
    refresh_token = create_refresh_token(data={"sub": db_user.username, "type": "refresh"})
    try:
        refresh_token_key = token_hash(refresh_token)
        redis_client.setex(f"refresh_token:{refresh_token_key}", settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60, "1")
    except Exception as e:
        logger.warning(f"刷新令牌存储失败(Redis异常, 已跳过): {e}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": db_user.id,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(auth_token: str = Header(..., description="Bearer + 刷新令牌, 例如: Bearer eyJhbG...")):
    token = auth_token.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="刷新令牌为空")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="刷新令牌无效, 登出失败")
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="令牌类型错误, 登出失败")
    try:
        token_key = token_hash(token)
        redis_client.delete(f"refresh_token:{token_key}")
    except Exception as e:
        logger.warning(f"刷新令牌删除失败(Redis异常, 已跳过): {e}")
        raise HTTPException(status_code=500, detail="登出失败, 服务端会话清除失败, 本地令牌将在短时间内自动失效")
    return {"detail": "登出成功"}

@router.get("/users/me", response_model=UserProfile)
def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user

@router.put("/users/me", response_model=UserProfile)
def update_user_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新当前用户资料"""
    update_data = user_update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(current_user, key, value)

    db.commit()
    db.refresh(current_user)
    return current_user