"""
分类路由模块
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func

from app.database import get_db
from app.models import Category, Article, User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/categories", tags=["分类"])

# ========== Pydantic 模型 ==========

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class CategoryResponse(BaseModel):
    id: int
    name: str
    articles_count: int = 0

    class Config:
        from_attributes = True


# ========== 路由 ==========

@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """创建分类"""
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """获取所有分类 (优化: 避免N+1查询) """
    results = (
        db.query(
            Category.id,
            Category.name,
            func.count(Article.id).label("articles_count")
        )
        .outerjoin(Article, Article.category_id == Category.id)
        .group_by(Category.id)
        .all()
    )

    return [
        CategoryResponse(id=r.id, name=r.name, articles_count=r.articles_count)
        for r in results
    ]


@router.get("/{category_id}/articles")
def get_category_articles(category_id: int, db: Session = Depends(get_db)):
    """获取分类下的所有文章"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    articles = db.query(Article).filter(Article.category_id == category_id).all()
    return {
        "category": category.name,
        "articles": articles
    }


@router.delete("/{category_id}")
def delete_category(
        category_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)):
    """删除分类（仅管理员可删除，关联文章category_id设为NULL）"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权操作, 仅管理员可删除分类")

    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    db.query(Article).filter(Article.category_id == category_id).update({"category_id": None})
    db.delete(category)
    db.commit()
    return {"message": "删除成功"}