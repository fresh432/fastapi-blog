"""
标签路由模块
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tag, Article

router = APIRouter(prefix="/tags", tags=["标签"])

@router.post("", status_code=201)
def create_tag(name: str, db: Session = Depends(get_db)):
    """创建标签"""
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="标签已存在")

    tag = Tag(name = name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

@router.get("")
def list_tags(db: Session = Depends(get_db)):
    """获取所有标签"""
    return db.query(Tag).all()

@router.post("/{article_id}/tags/{tag_id}")
def add_tag_to_article(article_id: int, tag_id: int, db: Session = Depends(get_db)):
    """给文章添加标签"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    article.tags.append(tag)
    db.commit()
    return {"message": "标签添加成功"}

@router.get("{tag_id}/articles")
def get_tag_articles(tag_id: int, db: Session = Depends(get_db)):
    """获取标签下的所有文章"""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    return {
        "tag": tag.name,
        "articles": tag.articles
    }