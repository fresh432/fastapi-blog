"""
点赞路由模块
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Like, Article, User
from app.auth import decode_token
from fastapi.security import OAuth2PasswordBearer

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
    """点赞文章"""
    # 检查文章存在
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 检查是否已点赞
    existing = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.article_id == article_id
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="已点赞")

    like = Like(user_id=current_user.id, article_id=article_id)
    db.add(like)
    db.commit()

    # 返回点赞数
    count = db.query(Like).filter(Like.article_id == article_id).count()
    return {"message": "点赞成功", "likes_count": count}

@router.delete("/{article_id}")
def unlike_article(
    article_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消点赞"""
    like = db.query(Like).filter(
        Like.user_id == current_user.id,
        Like.article_id == article_id
    ).first()

    if not like:
        raise HTTPException(status_code=404, detail="未点赞")

    db.delete(like)
    db.commit()

    count = db.query(Like).filter(Like.article_id == article_id).count()
    return {"message": "取消点赞成功", "likes_count": count}

@router.get("/{article_id}/count")
def get_likes_count(article_id: int, db: Session = Depends(get_db)):
    """获取文章点赞数"""
    count = db.query(Like).filter(Like.article_id == article_id).count()
    return {"article_id": article_id, "likes_count": count}