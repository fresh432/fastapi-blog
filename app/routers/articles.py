"""
文章路由模块
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import or_

from app.database import get_db
from app.models import Article, Category, Comment, User
from app.auth import decode_token
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(prefix="/articles", tags=["文章"])

# ========== Pydantic 模型 ==========

class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    category_id: Optional[int] = None

class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    category_id: Optional[int] = None
    author: Optional[str] = None

class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    author: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    comments_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

# ========== 依赖：获取当前用户 ==========

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

@router.get("/search")
def search_articles(
        q: str = Query(..., min_length=1, description="搜索关键词"),
        skip: int = Query(0, ge=0, description="跳过条数"),
        limit: int = Query(10, ge=1, le=100, description="每页条数"),
        db: Session = Depends(get_db)
):
    """搜索文章 (支持分页)"""
    query = db.query(Article).filter(
        or_(
            Article.title.contains(q),
            Article.content.contains(q)
        )
    )

    total = query.count()
    articles = query.order_by(Article.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "articles": articles
    }

@router.post("", response_model=ArticleResponse, status_code=201)
def create_article(
        article: ArticleCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建文章"""
    if article.category_id:
        category = db.query(Category).filter(Category.id == article.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

    db_article = Article(
        title=article.title,
        content=article.content,
        author=current_user.username,
        category_id=article.category_id
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


@router.get("", response_model=List[ArticleResponse])
def list_articles(db: Session = Depends(get_db)):
    """获取所有文章"""
    return db.query(Article).all()


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """获取单篇文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    response = ArticleResponse(
        id=article.id,
        title=article.title,
        content=article.content,
        author=article.author,
        category_id=article.category_id,
        created_at=article.created_at
    )

    if article.category_id:
        category = db.query(Category).filter(Category.id == article.category_id).first()
        if category:
            response.category_name = category.name

    response.comments_count = db.query(Comment).filter(Comment.article_id == article_id).count()
    return response


@router.put("/{article_id}", response_model=ArticleResponse)
def update_article(
        article_id: int,
        article_update: ArticleUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新文章"""
    db_article = db.query(Article).filter(Article.id == article_id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="文章不存在")

    update_data = article_update.model_dump(exclude_unset=True)
    if "category_id" in update_data and update_data["category_id"] is not None:
        category = db.query(Category).filter(Category.id == update_data["category_id"]).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

    for key, value in update_data.items():
        setattr(db_article, key, value)

    db.commit()
    db.refresh(db_article)
    return db_article


@router.delete("/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    """删除文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"message": "删除成功"}