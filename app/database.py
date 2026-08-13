"""
FastAPI 博客系统 - 数据库配置(MySQL版)
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

from app.core.config import settings

# MySQL 配置从统一配置中心读取
DB_PASSWORD = quote_plus(settings.DB_PASSWORD)

SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{settings.DB_USER}:{DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True
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
