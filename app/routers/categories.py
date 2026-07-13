"""
分类路由模块
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models_Category import Category
from app.models_Article import Article

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
    """获取所有分类"""
    categories = db.query(Category).all()

    result = []
    for category in categories:
        count = db.query(Article).filter(Article.category_id == category.id).count()
        cat_response = CategoryResponse(
            id=category.id,
            name=category.name,
            articles_count=count
        )
        result.append(cat_response)

    return result


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
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除分类（关联文章category_id设为NULL）"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    db.query(Article).filter(Article.category_id == category_id).update({"category_id": None})
    db.delete(category)
    db.commit()
    return {"message": "删除成功"}