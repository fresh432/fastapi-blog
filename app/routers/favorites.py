"""
收藏路由模块
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Favorite, Article, User
from app.tasks import delete_cache_delayed, safe_delay
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.cache import delete_cache, delete_cache_pattern

router = APIRouter(prefix="/favorites", tags=["收藏"])

@router.post("/{article_id}")
@limiter.limit("10/minute")
def favorite_article(
        request: Request,
        article_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """收藏文章"""
    # 检查文章存在
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    try:
        favorite = Favorite(user_id=current_user.id, article_id=article_id)
        db.add(favorite)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="已收藏")

    # 返回收藏数
    count = db.query(Favorite).filter(Favorite.article_id == article_id).count()

    # 清除文章缓存
    delete_cache(f"fastapi:article:{article_id}")
    delete_cache_pattern("fastapi:articles:list:*")

    # 延迟双删
    safe_delay(
        delete_cache_delayed,
        f"fastapi:article:{article_id}",
        "fastapi:articles:list:*",
        countdown=2
    )

    return {"message": "收藏成功", "favorites_count": count}

@router.delete("/{article_id}")
@limiter.limit("10/minute")
def unfavorite_article(
        request: Request,
        article_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """取消收藏"""
    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.article_id == article_id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="未收藏")

    try:
        db.delete(favorite)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="取消收藏失败, 请稍后重试")

    count = db.query(Favorite).filter(Favorite.article_id == article_id).count()

    # 清除文章缓存
    delete_cache(f"fastapi:article:{article_id}")
    delete_cache_pattern("fastapi:articles:list:*")

    # 延迟双删
    safe_delay(
        delete_cache_delayed,
        f"fastapi:article:{article_id}",
        "fastapi:articles:list:*",
        countdown=2
    )

    return {"message": "取消收藏成功", "favorites_count": count}

@router.get("/me")
@limiter.limit("10/minute")
def list_favorites(
        request: Request,
        skip: int = Query(0, ge=0, description="跳过条数"),
        limit: int = Query(10, ge=1, le=100, description="每页条数"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """获取当前用户收藏列表"""
    query = db.query(Article).join(Favorite).filter(Favorite.user_id == current_user.id)
    articles = query.order_by(Favorite.created_at.desc()).offset(skip).limit(limit).all()
    total = query.count()

    result = {
        "total": total,
        "skip": skip,
        "limit": limit,
        "articles": [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "author": a.author,
                "category_id": a.category_id,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in articles
        ]
    }

    return result
