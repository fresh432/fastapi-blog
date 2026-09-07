"""
评论路由模块
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Comment, Article, User
from app.core.dependencies import get_current_user

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

@router.get("/article/{article_id}")
def get_article_comments(
    article_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """"获取文章评论 (支持分页) """
    comments = db.query(Comment).filter(Comment.article_id == article_id).offset(skip).limit(limit).all()
    total = db.query(Comment).filter(Comment.article_id == article_id).count()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "comments": comments
    }