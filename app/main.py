"""
FastAPI 博客系统 - 主入口（路由拆分版）

并发模型说明：
- Web 层（articles/users/comments等）：同步路由，FastAPI自动提交到线程池执行
  原因：SQLAlchemy 1.x同步版稳定，当前并发量下线程池足够，预留async迁移路径
- AI 层（ai/chat/agent）：异步路由，基于asyncio+uvloop（epoll封装）
  原因：LLM API调用是IO密集型，异步可避免阻塞，支持SSE流式响应
- Celery：prefork进程池，适合CPU密集型任务（文章摘要、数据统计）
"""

from fastapi import FastAPI, Request
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter
from slowapi.errors import RateLimitExceeded
from app.database import engine, Base

# 导入路由
from app.routers import articles, categories, users, comments, tags, likes, ai

# 建表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 实例
app = FastAPI(
    title="个人博客系统",
    description="学习 FastAPI 的后端项目（路由拆分版）",
    version="0.2.0"
)

# 注册限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
app.include_router(articles.router)
app.include_router(categories.router)
app.include_router(users.router)
app.include_router(comments.router)
app.include_router(tags.router)
app.include_router(likes.router)
app.include_router(ai.router)


@app.get("/")
def read_root():
    return {"message": "个人博客系统", "docs": "/docs"}


# ========== 启动时添加测试数据 + 缓存预热 ==========

from app.database import SessionLocal
from app.models import Article
import json

@app.on_event("startup")
def init_data():
    """启动时添加测试数据"""
    db = SessionLocal()
    try:
        # 1. 测试数据 (仅空表时添加)
        if db.query(Article).count() == 0:
            test_articles = [
                Article(title="第一篇", content="Hello FastAPI", author="fresh432"),
                Article(title="第二篇", content="学习笔记", author="fresh432")
            ]
            for article in test_articles:
                db.add(article)
            db.commit()

        # 2. 缓存预热: 加载热门文章到Redis
        from app.core.cache import set_cache

        hot_articles = db.query(Article).filter(
            Article.status == "published"
        ).order_by(Article.created_at.desc()).limit(20).all()

        for article in hot_articles:
            cache_key = f"fastapi:article:{article.id}"
            result = {
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "author": article.author,
                "category_id": article.category_id,
                "status": article.status,
                "created_at": article.created_at.isoformat() if article.created_at else None
            }
            set_cache(cache_key, json.dumps(result), base_expire=600)
    finally:
        db.close()