"""
统一依赖：用户认证
"""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer

from app.database import get_db
from app.models import User
from app.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前登录用户 (统一认证依赖) """
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的Token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token中无用户信息")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user