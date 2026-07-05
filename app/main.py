"""
FastAPI 博客系统 - 文章 CRUD（数据库版）
"""

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db, SessionLocal
from app.models_Article import Article
from app.models_User import User
from app.models_Category import Category
from app.models_Comment import Comment
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from app.auth import verify_password, get_password_hash, create_access_token, decode_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, oauth2

# OAuth2密码流, token获取地址
oauth2_schem = OAuth2PasswordBearer(tokenUrl="token")

# 建表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 实例
app = FastAPI(
    title="个人博客系统",
    description="学习 FastAPI 的后端项目",
    version="0.1.0"
)


# ========== Pydantic 模型（请求验证）==========

class ArticleCreate(BaseModel):
    """创建文章请求模型"""
    title: str = Field(..., min_length=1, max_length=100, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    category_id: Optional[int] = None # 新增: 可选分类


class ArticleResponse(BaseModel):
    """文章响应模型（用于序列化）"""
    id: int
    title: str
    content: str
    author: str
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    comments_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True  # 允许从 ORM 对象转换

class UserCreate(BaseModel):
    """用户注册/登录请求"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)

class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str

    class Config:
        from_attributes = True

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

class CategoryResponse(BaseModel):
    id: int
    name: str
    articles_count: int = 0

    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, description="评论内容")
    article_id: int = Field(..., description="文章ID")

class CommentResponse(BaseModel):
    id: int
    content: str
    author: str
    article_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ========== 基础路由 ==========

@app.get("/")
def read_root():
    return {"message": "个人博客系统", "docs": "/docs"}

def get_current_user(token: str = Depends(oauth2_schem), db: Session = Depends(get_db)):
    """依赖项: 验证Token并返回当前用户"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="无效的Token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Token中无用户信息")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return user

# ========== 文章 CRUD（数据库版）==========

@app.post("/articles", response_model=ArticleResponse, status_code=201)
def create_article(
    article: ArticleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建文章 (可选分类)"""
    # 如果有分类ID, 验证分类是否存在
    if article.category_id:
        category = db.query(Category).filter(Category.id == article.category_id).first()
        if not category:
            raise HTTPException(satus_code=404, detail="分类不存在")

    db_article = Article(
        title=article.title,
        content=article.content,
        author=current_user.username,
        category_id=article.category_id # 新增
    )
    db.add(db_article)
    db.commit()
    db.refresh(db_article)
    return db_article


@app.get("/articles", response_model=List[ArticleResponse])
def list_articles(db: Session = Depends(get_db)):
    """获取所有文章"""
    return db.query(Article).all()


@app.get("/articles/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """获取单篇文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 构建响应, 填充分类名称
    response = ArticleResponse(

        id=article.id,
        title=article.title,
        content=article.content,
        author=article.author,
        category_id=article.category_id,
        created_at=article.created_at
    )

    # 如果有分类, 查询名称
    if article.category_id:
        category = db.query(Category).filter(Category.id == article.category_id).first()
        if category:
            response.category_name = category.name

    # 评论数量
    response.comments_count = db.query(Comment).filter(Comment.article_id == article_id).count()

    return response


@app.delete("/articles/{article_id}")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    """删除文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    db.delete(article)
    db.commit()
    return {"message": "删除成功"}

class ArticleUpdate(BaseModel):
    """更新文章请求体模型(所有字段可选)"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None, min_length=1)
    category_id: Optional[int] = None
    author: Optional[str] = None

@app.put("/articles/{article_id}", response_model=ArticleResponse)
def update_article(
        article_id: int,
        article_update: ArticleUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """更新文章(支持修改分类)"""
    # 1. 查询文章
    db_article = db.query(Article).filter(Article.id == article_id).first()

    # 2. 不存在则报错
    if not db_article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 3. 只更新传入的字段
    update_data = article_update.model_dump(exclude_unset=True)
    # 如果修改了分类, 验证分类是否存在
    if "category_id" in update_data and update_data["category_id"] is not None:
        category = db.query(Category).filter(Category.id == update_data["category_id"]).first()
        if not category:
            raise HTTPException(status_code=404, detail="分类不存在")

    for key, value in update_data.items():
        setattr(db_article, key, value)

    # 4. 提交并返回
    db.commit()
    db.refresh(db_article)
    return db_article

# ========== 文章类别 ==========

# 创建分类
@app.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Category(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

# 获取所有分类
@app.get("/categories", response_model=List[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    """获取所有分类 (含文章数量)"""
    categories = db.query(Category).all()

    result = []
    for category in categories:
        # 统计该分类下的文章数量
        count = db.query(Article).filter(Article.category_id == category.id).count()

        cat_response = CategoryResponse(
            id=category.id,
            name=category.name,
            articles_count=count
        )
        result.append(cat_response)

    return result

# 获取某个分类下的所有文章
@app.get("/categories/{category_id}/articles")
def get_category_articles(category_id: int, db: Session = Depends(get_db)):
    """获取分类下的所有文章"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise  HTTPException(status_code=404, detail="分类不存在")

    # 查询该分类下的文章
    articles = db.query(Article).filter(Article.category_id == category_id).all()
    return {
        "category": category.name,
        "articles": articles
    }

@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    """删除分类 (关联文章category_id设为NULL) """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    # 将关联文章的category_id设为NULL
    db.query(Article).filter(Article.category_id == category_id).update({"category_id": None})

    db.delete(category)
    db.commit()
    return {"message": "删除成功"}

# ========== 用户注册/登录 ==========

@app.post("/token")
def login_for_access_token(
        from_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """
    OAuth2标准登录, 返回JWT Token
    请求格式: x-www-from-urlencoded (username + password)
    """
    # 查找用户
    user = db.query(User).filter(User.username == from_data.username).first()

    # 验证用户和密码
    if not user or not verify_password(from_data.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 创建Token
    access_token = create_access_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/register", response_model=UserResponse, status_code=201)
def register(user: UserCreate, db: Session = Depends(get_db)):
    """用户注册 (密码加密存储)"""
    # 检查用户名是否已存在
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 加密密码
    hashed_password = get_password_hash(user.password)

    # 创建用户
    db_user = User(username=user.username, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    """用户登录 (JSON格式, 兼容旧接口)"""
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    access_token = create_access_token(data={"sub": db_user.username})

    return {"access_token": access_token,
            "user_id": db_user.id,
            "token_type": "bearer"
    }

@app.get("/users/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息 (需要Token)"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "created_at": current_user.created_at
    }

# ========== 评论 CRUD ==========

@app.post("/comments", response_model=CommentResponse, status_code=201)
def create_comment(
        comment: CommentCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """创建评论"""
    # 验证文章存在
    article = db.query(Article).filter(Article.id == comment.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    db_comment = Comment(
        content=comment.content,
        author=current_user.username,
        article_id=comment.article_id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@app.delete("/comments/{comment_id}")
def delete_comment(
        comment_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    """删除评论 (只能删除自己的) """
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")

    # 只能删除自己的评论
    if comment.author != current_user.username:
        raise HTTPException(status_code=403, detail="无权删除他人评论")

    db.delete(comment)
    db.commit()
    return {"message": "删除成功"}

# ========== 启动时添加测试数据 ==========

@app.on_event("startup")
def init_data():
    """启动时添加测试数据"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(Article).count() == 0:
            test_articles = [
                Article(title="第一篇", content="Hello FastAPI", author="fresh432"),
                Article(title="第二篇", content="学习笔记", author="fresh432")
            ]
            for article in test_articles:
                db.add(article)
            db.commit()
    finally:
        db.close()