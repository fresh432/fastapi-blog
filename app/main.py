"""
FastAPI 博客系统 - 文章 CRUD（数据库版）
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db, SessionLocal
from app.models_Article import Article
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

# 建表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 实例
app = FastAPI(
    title="个人博客系统",
    description="学习 FastAPI 的后端项目",
    version="0.1.0"
)


# ========== Pydantic 模型（请求验证）==========

class ArticleCreate(BaseModel):
    """创建文章请求模型"""
    title: str = Field(..., min_length=1, max_length=100, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    author: str = "匿名"


class ArticleResponse(BaseModel):
    """文章响应模型（用于序列化）"""
    id: int
    title: str
    content: str
    author: str
    created_at: datetime

    class Config:
        from_attributes = True  # 允许从 ORM 对象转换


# ========== 基础路由 ==========

@app.get("/")
def read_root():
    return {"message": "个人博客系统", "docs": "/docs"}


# ========== 文章 CRUD（数据库版）==========

@app.post("/articles", response_model=ArticleResponse, status_code=201)
def create_article(article: ArticleCreate, db: Session = Depends(get_db)):
    """创建文章"""
    db_article = Article(
        title=article.title,
        content=article.content,
        author=article.author
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


@app.get("/articles", response_model=List[ArticleResponse])
def list_articles(db: Session = Depends(get_db)):
    """获取所有文章"""
    return db.query(Article).all()


@app.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """获取单篇文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


@app.delete("/articles/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    """删除文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"message": "删除成功"}


# ========== 启动时添加测试数据 ==========

@app.on_event("startup")
def init_data():
    """启动时添加测试数据"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(Article).count() == 0:
            test_articles = [
                Article(title="第一篇", content="Hello FastAPI", author="fresh432"),
                Article(title="第二篇", content="学习笔记", author="fresh432")
            ]
            for article in test_articles:
                db.add(article)
            db.commit()
    finally:
        db.close()