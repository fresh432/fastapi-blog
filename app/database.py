"""
FastAPI 博客系统 - 数据库配置(MySQL版)
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# MySQL 配置从统一配置中心读取

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,     # 连接存活检测, 防止TCP半开连接
    pool_size=10,           # 常驻连接数, 减少三次握手开销
    max_overflow=20,        # 峰值额外连接
    pool_recycle=3600,      # 1小时回收, 配合MySQL wait_timeout
    pool_timeout=30,        # 获取连接超时
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """依赖注入: 获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
