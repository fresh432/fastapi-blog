"""
点赞路由模块
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Like, Article, User
from app.auth import decode_token
from fastapi.security import OAuth2PasswordBearer
from app.core.cache import delete_cache, delete_cache_pattern

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(prefix="/likes", tags=["点赞"])


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的Token")

    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user


@router.post("/{article_id}")
def like_article(
        article_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """点赞文章 (原子操作，唯一约束兜底) """
    # 检查文章存在
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    try:
        like = Like(user_id=current_user.id, article_id=article_id)
        db.add(like)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="已点赞")

    # 返回点赞数
    count = db.query(Like).filter(Like.article_id == article_id).count()

    # 清除文章缓存
    delete_cache(f"fastapi:article:{article_id}")
    delete_cache_pattern("fastapi:articles:list:*")

    return {"message": "点赞成功", "likes_count": count}

@router.delete("/{article_id}")
def unlike_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消点赞（事务包裹，异常回滚）"""
    like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.article_id == article_id
    ).first()

    if not like:
        raise HTTPException(status_code=404, detail="未点赞")

    try:
        db.delete(like)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="取消点赞失败, 请稍后重试")

    count = db.query(Like).filter(Like.article_id == article_id).count()

    # 清除文章缓存
    delete_cache(f"fastapi:article:{article_id}")
    delete_cache_pattern("fastapi:articles:list:*")

    return {"message": "取消点赞成功", "likes_count": count}

@router.get("/{article_id}/count")
def get_likes_count(article_id: int, db: Session = Depends(get_db)):
    """获取文章点赞数"""
    count = db.query(Like).filter(Like.article_id == article_id).count()
    return {"article_id": article_id, "likes_count": count}