"""
文章 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Article(Base):
    """文章表"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(50), default="匿名")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联评论
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")

    # 关联标签
    tags = relationship("Tag", secondary="article_tag", back_populates="articles")