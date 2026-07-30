# FastAPI Blog API

基于 FastAPI 构建的现代化博客后端 API，支持 JWT 认证、Redis 缓存、Celery 异步任务、Docker 容器化部署。

## 技术栈

- **框架**: FastAPI + SQLAlchemy + Pydantic
- **数据库**: SQLite（开发）/ PostgreSQL（生产）
- **缓存**: Redis（缓存 + 空值缓存防穿透 + 随机过期防雪崩）
- **异步任务**: Celery + Redis
- **限流**: slowapi
- **容器化**: Docker + Docker Compose
- **测试**: pytest

## 功能列表

| 模块 | 功能 |
|------|------|
| 用户 | 注册 / 登录 / JWT认证 / 获取资料 / 更新资料 |
| 文章 | CRUD / 搜索 / 分页 / 草稿状态 / Redis缓存 |
| 分类 | CRUD / 文章关联 / 删除置NULL |
| 评论 | 创建 / 列表 / 级联删除 |
| 点赞 | 点赞 / 取消点赞 / 计数 |
| 系统 | API限流 / 异步邮件 / 阅读量统计 / 单元测试 |

## 快速开始

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务
uvicorn app.main:app --reload

# 3. 访问文档
http://localhost:8000/docs
```

## Docker 部署
```bash
docker-compose up --build -d
```

## 项目结构
```plain
fastapi-blog/
├── app/                    # 核心应用代码
│   ├── core/               # 核心配置与基础设施
│   │   ├── cache.py        # Redis 缓存逻辑封装
│   │   ├── celery_app.py   # Celery 异步任务实例初始化
│   │   └── limiter.py      # 接口限流配置 (Rate Limiting)
│   ├── models/             # 数据库模型层 (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── article.py      # 文章模型
│   │   ├── category.py     # 分类模型
│   │   ├── comment.py      # 评论模型
│   │   ├── like.py         # 点赞模型
│   │   ├── tag.py          # 标签模型
│   │   └── user.py         # 用户模型
│   ├── routers/            # API 路由层 (Endpoint 定义)
│   │   ├── __init__.py
│   │   ├── articles.py     # 文章相关接口 (CRUD)
│   │   ├── categories.py   # 分类管理接口
│   │   ├── comments.py     # 评论交互接口
│   │   ├── likes.py        # 点赞功能接口
│   │   ├── tags.py         # 标签管理接口
│   │   └── users.py        # 用户注册/登录/信息接口
│   ├── __init__.py
│   ├── auth.py             # JWT 认证与权限校验逻辑
│   ├── database.py         # 数据库连接会话 (SessionLocal, Engine)
│   ├── main.py             # FastAPI 应用入口
│   └── tasks.py            # 异步任务定义 (配合 Celery 使用)
├── tests/                  # 单元测试目录
│   ├── __init__.py
│   ├── conftest.py         # Pytest 全局配置与 Fixture
│   └── test_articles.py    # 文章模块测试用例
├── .env                    # 环境变量配置文件 (需自行创建，参考 .env.example)
├── .gitignore              # Git 忽略规则
├── docker-compose.yml      # Docker 编排文件 (Web, MySQL, Redis)
├── Dockerfile              # Web 服务构建文件
├── requirements.txt        # Python 依赖列表
└── README.md               # 项目说明文档
```

## API文档
启动后访问 /docs 查看 Swagger 自动生成的交互式文档。