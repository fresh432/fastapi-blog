"""
用户路由模块
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm

from app.tasks import send_welcome_email
from app.database import get_db
from app.models import User
from app.auth import verify_password, get_password_hash, create_access_token
from app.core.dependencies import get_current_user
from app.core.cache import redis_client

import logging

router = APIRouter(tags=["用户"])

logger = logging.getLogger(__name__)

# ========== 登录防爆破 ==========
LOGIN_MAX_FAILS = 5         # 最大连接失败次数
LOGIN_LOCK_SECONDS = 600    # 锁定时长: 10分钟

def _login_fail_key(username: str) -> str:
    return f"login:fail:{username}"

def _login_lock_key(username: str) -> str:
    return f"login:lock:{username}"

def _check_login_locked(username: str) -> bool:
    """检查账号是否被锁定 (Redis异常时降级放行, 不阻塞正常登录)"""
    try:
        return redis_client.get(_login_lock_key(username)) is not None
    except Exception as e:
        logger.warning(f"登录锁定检查失败(Redis异常), 降级放行: {e}")
        return False

def _record_login_fail(username: str):
    """记录登录失败, 连续失败5次锁定10分钟 (Redis异常时静默跳过)"""
    try:
        fail_key = _login_fail_key(username)
        fails = redis_client.incr(fail_key)
        if fails == 1:
            redis_client.expire(fail_key, LOGIN_LOCK_SECONDS)
        if fails >= LOGIN_MAX_FAILS:
            redis_client.setex(_login_lock_key(username), LOGIN_LOCK_SECONDS, "1")
            redis_client.delete(fail_key)
            logger.warning(f"用户 {username} 连续登录失败{LOGIN_MAX_FAILS}次, 账号锁定10分钟")
    except Exception as e:
        logger.warning(f"登录失败计数异常(Redis异常), 跳过计数: {e}")

def _clear_login_fail(username: str):
    """登录成功后清除失败计数"""
    try:
        redis_client.delete(_login_fail_key(username))
    except Exception:
        pass

# ========== Pydantic 模型 ==========

from pydantic import BaseModel, Field
from typing import Optional

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
    password: str = Field(..., min_length=6, max_length=100)


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
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _clear_login_fail(form_data.username)
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
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
    try:
        send_welcome_email.delay(db_user.username)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"欢迎邮件任务发送失败, 用户ID: {db_user.id}, 已降级跳过: {e}")

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
    access_token = create_access_token(data={"sub": db_user.username})
    return {
        "access_token": access_token,
        "user_id": db_user.id,
        "token_type": "bearer"
    }


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