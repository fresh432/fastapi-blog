"""
FastAPI 博客系统 - 主入口（路由拆分版）
"""

from fastapi import FastAPI
from app.database import engine, Base

# 导入路由
from app.routers import articles, categories, users, comments

# 建表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 实例
app = FastAPI(
    title="个人博客系统",
    description="学习 FastAPI 的后端项目（路由拆分版）",
    version="0.2.0"
)

# 注册路由
app.include_router(articles.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(comments.router)


@app.get("/")
def read_root():
    return {"message": "个人博客系统", "docs": "/docs"}


# ========== 启动时添加测试数据 ==========

from app.database import SessionLocal
from app.models_Article import Article

@app.on_event("startup")
def init_data():
    """启动时添加测试数据"""
    db = SessionLocal()
    try:
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