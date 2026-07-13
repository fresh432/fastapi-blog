"""
评论路由模块
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Comment, Article, User
from app.auth import decode_token
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(prefix="/comments", tags=["评论"])

# ========== Pydantic 模型 ==========

from pydantic import BaseModel, Field
from datetime import datetime


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, description="评论内容")
    article_id: int = Field(..., description="文章ID")


class CommentResponse(BaseModel):
    id: int
    content: str
    author: str
    article_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 依赖 ==========

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
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


# ========== 路由 ==========

@router.post("", response_model=CommentResponse, status_code=201)
def create_comment(
        comment: CommentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建评论"""
    article = db.query(Article).filter(Article.id == comment.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    db_comment = Comment(
        content=comment.content,
        author=current_user.username,
        article_id=comment.article_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@router.delete("/{comment_id}")
def delete_comment(
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除评论（只能删除自己的）"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    if comment.author != current_user.username:
        raise HTTPException(status_code=403, detail="无权删除他人评论")

    db.delete(comment)
    db.commit()
    return {"message": "删除成功"}