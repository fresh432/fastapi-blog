"""
收藏 ORM 模型
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联文章
    article = relationship("Article", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint('user_id', 'article_id', name='uix_user_article_favorite'),
    )