# FastAPI Blog API

基于 FastAPI 构建的现代化博客后端 API，支持 JWT 认证、Redis 缓存、Celery 异步任务、AI 智能体（LLM 对话 / RAG 知识库 / Agent 工具调用）、Docker 容器化部署。

## 技术栈

- **框架**: FastAPI + SQLAlchemy + Pydantic
- **数据库**: MySQL 8.0（生产）/ SQLite（开发可选）
- **缓存**: Redis（缓存 + 空值缓存防穿透 + 随机过期防雪崩）
- **异步任务**: Celery + Redis
- **限流**: slowapi
- **向量库**: Chroma（RAG 知识库持久化）
- **容器化**: Docker + Docker Compose
- **测试**: pytest

## 功能列表

### 核心模块

| 模块 | 功能 |
|------|------|
| 用户 | 注册 / 登录 / JWT 认证 / 获取资料 / 更新资料 |
| 文章 | CRUD / 搜索 / 分页 / 草稿状态 / Redis 缓存 |
| 分类 | CRUD / 文章关联 / 删除置 NULL |
| 评论 | 创建 / 列表 / 分页 / 级联删除 |
| 标签 | 创建 / 列表 / 文章关联（多对多） |
| 点赞 | 点赞 / 取消点赞 / 计数 |

### AI 模块

| 接口 | 功能 |
|------|------|
| `/ai/chat` | LLM 非流式对话（支持历史记录） |
| `/ai/chat/stream` | LLM SSE 流式对话 |
| `/ai/summarize` | 文章智能摘要（结构化 JSON 输出） |
| `/ai/upload` | 文档上传知识库（txt/md，限制 5MB） |
| `/ai/ask` | 基于知识库问答（Hybrid Search，空检索降级） |
| `/ai/agent` | Agent 智能体对话（工具调用 + 记忆持久化） |
| `/ai/agent/stream` | Agent SSE 流式（实时返回工具调用过程） |

## 快速开始

### 1. 环境变量

复制 `.env.example` 为 `.env`，填写以下配置：

```env
# 数据库
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=blog

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# JWT
SECRET_KEY=your-secret-key-change-in-production

# LLM (DeepSeek / OpenAI 兼容)
LLM_API_KEY=your-llm-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=30

# Embedding (通义千问)
QW_API_KEY=your-qwen-api-key
```

### 2. 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload

# 访问 Swagger 文档
http://localhost:8000/docs
```

### 3. Docker 部署

```bash
# 一键启动（Web + MySQL + Redis）
docker-compose up --build -d

# 查看日志
docker-compose logs web --tail=50

# 停止并清理
docker-compose down -v
```

### 4. 启动 Celery Worker（可选，异步任务）

```bash
celery -A app.core.celery_app worker --loglevel=info
```

## 项目结构

```plain
fastapi-blog/
├── app/                          # 核心应用代码
│   ├── core/                     # 核心配置与基础设施
│   │   ├── cache.py              # Redis 缓存逻辑封装
│   │   ├── celery_app.py         # Celery 异步任务实例初始化
│   │   ├── config.py             # 统一配置中心（数据库/Redis/JWT/LLM）
│   │   └── limiter.py            # 接口限流配置 (Rate Limiting)
│   ├── models/                   # 数据库模型层 (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── article.py            # 文章模型
│   │   ├── category.py           # 分类模型
│   │   ├── comment.py            # 评论模型
│   │   ├── like.py               # 点赞模型
│   │   ├── tag.py                # 标签模型（多对多关联）
│   │   └── user.py               # 用户模型
│   ├── routers/                  # API 路由层 (Endpoint 定义)
│   │   ├── __init__.py
│   │   ├── ai.py                 # AI 模块接口（LLM / RAG / Agent）
│   │   ├── articles.py           # 文章相关接口 (CRUD / 搜索 / 草稿)
│   │   ├── categories.py         # 分类管理接口
│   │   ├── comments.py           # 评论交互接口
│   │   ├── likes.py              # 点赞功能接口
│   │   ├── tags.py               # 标签管理接口
│   │   └── users.py              # 用户注册/登录/信息接口
│   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   └── ai.py                 # AI 模块请求/响应模型
│   ├── services/                 # 业务逻辑层
│   │   ├── agent.py              # LangGraph Agent 核心（工具调用）
│   │   ├── agent_memory.py       # Agent 记忆持久化（Redis）
│   │   ├── chat_history.py       # LLM 对话历史（Redis）
│   │   ├── llm.py                # LLM 客户端单例封装
│   │   └── rag.py                # RAG 核心（Hybrid Search 混合检索）
│   ├── __init__.py
│   ├── auth.py                   # JWT 认证与密码加密（bcrypt 4.x 兼容）
│   ├── database.py               # 数据库连接会话（MySQL + pymysql）
│   ├── main.py                   # FastAPI 应用入口
│   └── tasks.py                  # Celery 异步任务定义
├── chroma_db/                    # Chroma 向量库持久化目录
├── tests/                        # 单元测试目录
│   ├── __init__.py
│   ├── conftest.py               # Pytest 全局配置与 Fixture
│   └── test_articles.py          # 文章模块测试用例
├── uploads/                      # 文档上传目录（RAG 知识库）
├── .env                          # 环境变量配置文件
├── .env.example                  # 环境变量模板
├── .gitignore
├── docker-compose.yml            # Docker 编排文件 (Web + MySQL + Redis)
├── Dockerfile                    # Web 服务构建文件
├── requirements.txt              # Python 依赖列表
├── README.md                     # 项目说明文档
└── docs/                         # 接口测试报告与文档
    └── api_test_report.md        # 接口全量测试报告
```

## API 文档

启动后访问 `/docs` 查看 Swagger 自动生成的交互式文档。

### 认证方式

所有需要登录的接口在 Header 中携带：

```
Authorization: Bearer {access_token}
```

### 核心接口速查

| 模块 | 接口 | 方法 | 说明 |
|------|------|------|------|
| 用户 | `/register` | POST | 用户注册 |
| 用户 | `/login` | POST | JSON 登录 |
| 用户 | `/token` | POST | OAuth2 登录（Swagger 用） |
| 文章 | `/articles` | GET | 文章列表（支持缓存） |
| 文章 | `/articles` | POST | 创建文章（需登录） |
| 文章 | `/articles/{id}` | PUT | 更新文章（仅作者） |
| 文章 | `/articles/{id}` | DELETE | 删除文章（仅作者） |
| AI | `/ai/chat` | POST | LLM 对话（需登录） |
| AI | `/ai/chat/stream` | POST | SSE 流式对话（需登录） |
| AI | `/ai/upload` | POST | 上传文档到知识库 |
| AI | `/ai/ask` | POST | 知识库问答（需登录） |
| AI | `/ai/agent` | POST | Agent 智能体对话（需登录） |
| AI | `/ai/agent/stream` | POST | Agent 流式对话（需登录） |

## 接口测试报告

详见 `docs/api_test_report.md`，包含：
- 33 个接口全量测试结果（全部通过）
- 5 个 bug 发现与修复记录
- 权限安全验证
- 性能与缓存验证

## 生产部署架构
```plain
┌─────────────┐     HTTPS      ┌─────────────┐     HTTP/1.1     ┌─────────────┐
│   客户端     │ ─────────────→ │    Nginx    │ ───────────────→ │   Uvicorn   │
│ (浏览器/APP) │   (TLS 1.2/1.3)│ 反向代理+SSL │  Keep-Alive长连接 │  (FastAPI)  │
└─────────────┘                └─────────────┘                  └─────────────┘
│
↓
┌─────────────┐
│  MySQL 8.0  │
└─────────────┘
│
↓
┌─────────────┐
│    Redis    │
└─────────────┘
```

### Nginx 核心作用

| 功能 | 说明 |
|------|------|
| SSL 终止 | Nginx 处理 HTTPS 解密，后端走 HTTP，减轻 Uvicorn 加密负担 |
| Keep-Alive 管理 | 统一控制连接超时和最大请求数，防止空闲连接占用资源 |
| 静态文件服务 | Nginx 直接返回静态资源，不经过 Uvicorn |
| 负载均衡 | 多实例 Uvicorn 时，Nginx 轮询分发请求 |

### 生产环境启动

```bash
# 使用生产版编排（含 Nginx + SSL）
docker-compose -f docker-compose.prod.yml up -d
```

## 部署注意事项

1. **MySQL 密码特殊字符**：如密码含 `@` 等特殊字符，`database.py` 已使用 `quote_plus` 进行 URL 编码
2. **bcrypt 4.x 兼容**：`auth.py` 使用原生 bcrypt 并截断 72 字节，避免 `passlib` 兼容问题
3. **Chroma 持久化**：Docker 部署时需挂载 `chroma_db` 目录，确保向量数据不丢失
4. **LLM API Key**：AI 模块依赖外部 LLM 服务，请确保 `.env` 中配置有效 Key
5. **Nginx Keep-Alive**：生产环境通过 Nginx 反向代理管理长连接，配置 `keepalive_timeout` 和 `keepalive_requests` 防止空闲连接占用资源

## 许可证

本项目仅供学习和交流，采用 CC BY-NC 4.0 协议，禁止任何商业用途。
