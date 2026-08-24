"""
文章 ORM 模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Article(Base):
    """文章表"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    author = Column(String(50), default="匿名", index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    status = Column(String(20), default="published")
    version = Column(Integer, default=0, nullable=False) # 乐观锁版本号
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),onupdate=func.now())

    __table_args__ = (
        Index('idx_author_status', 'author', 'status'),
    )

    # 关联评论
    comments = relationship("Comment", back_populates="article", cascade="all, delete-orphan")

    # 关联标签
    tags = relationship("Tag", secondary="article_tag", back_populates="articles")