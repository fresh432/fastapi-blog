"""
FastAPI 博客系统 - 文章 CRUD
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

# 创建 FastAPI 实例
app = FastAPI(
    title = "个人博客系统",
    description = "学习 FastAPI 的后端项目",
    version = "0.1.0"
)

# ========== Pydantic 模型 ==========

class ArticleCreate(BaseModel):
    """创建文章请求模型"""
    title: str = Field(..., min_length=1, max_length=100, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    author: str = Field(default="匿名", description="作者")

class Article(ArticleCreate):
    """文章完整模型 (含ID和时间)"""
    id: int
    created_at: datetime = Field(default_factory=datetime.now)

# ========== 内存数据库 ==========

articles_db: List[Article] = []
article_id_counter = 0

# ========== 基础路由 ==========

@app.get("/")
def read_root():
    return {"message": "个人博客系统", "docs": "/docs"}

# ========== 文章 CRUD ==========

@app.post("/articles", response_model=Article, status_code=201)
def create_article(article: ArticleCreate):
    """创建文章"""
    global article_id_counter

    article_id_counter += 1
    new_article = Article(
        id = article_id_counter,
        **article.model_dump() # 把 ArticleCreate 的字段展开
    )
    articles_db.append(new_article)

    return new_article

@app.get("/articles", response_model=List[Article])
def list_articles():
    """获取所有文章"""
    return articles_db

@app.get("/articles/{article_id}", response_model=Article)
def get_article(article_id: int):
    """获取单篇文章"""
    for article in articles_db:
        if article.id == article_id:
            return article

    raise HTTPException(status_code=404, detail="文章不存在")

@app.delete("/articles/{article_id}")
def delete_article(article_id: int):
    """删除文章"""
    for index, article in enumerate(articles_db):
        if article.id == article_id:
            articles_db.pop(index)
            return {"message": "删除成功"}

    raise HTTPException(status_code=404, detail="文章不存在")

# ========== 测试数据 ==========

@app.on_event("startup")
def init_data():
    """启动时添加测试数据"""
    global article_id_counter

    test_articles = [
        {"title": "第一篇", "content": "Hello FastAPI", "author": "fresh432"},
        {"title": "第二篇", "content": "学习笔记", "author": "fresh432"}
    ]

    for data in test_articles:
        article_id_counter += 1
        articles_db.append(Article(
            id = article_id_counter,
            **data
        ))