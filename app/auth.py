"""
密码加密与验证模块
"""

import os
import bcrypt
from datetime import datetime, timedelta
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# JWT配置 (生产环境应放置在环境变量)
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def _truncate_password(password: str) -> bytes:
    """
    bcrypt 4.x 限制明文密码最多 72 字节。
    超过则截断，避免 ValueError: password exceeds maximum length 72
    """
    pwd_bytes = password.encode('utf-8')
    if len(pwd_bytes) > 72:
        pwd_bytes = pwd_bytes[:72]
    return pwd_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配加密密码（兼容 bcrypt 4.x）"""
    pwd_bytes = _truncate_password(plain_password)
    hash_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


def get_password_hash(password: str) -> str:
    """加密密码（兼容 bcrypt 4.x）"""
    pwd_bytes = _truncate_password(password)
    return bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建JWT Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    """验证并解码Token, 返回payload或None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None