# CHANGELOG

> 本文件记录 2026-09-08 质量迭代启动以来的修复与改进。
> 项目初始开发阶段（2026-06 下旬 ~ 09 月初）的历史变更请见 git 提交记录。

## 2026-09-09
- 修复 `hybrid_search` 变量名错误（`fused_contents` → `fused`），消除 /ai/ask 与 Agent 知识库检索的 NameError
- 删除 Chroma 已废弃的 `persist()` 调用（新版自动持久化）
- 删除 `routers/ai.py` 未使用的 `langchain_classic` 导入，消除干净环境 ImportError
- 移除无关依赖 `booktype`（Python 2 语法残留导致安装/运行报错）

## 2026-09-10
- `celery_app.py` 复用 `settings.CELERY_BROKER_URL/RESULT_BACKEND`，删除写死的 host/端口，修复空密码时非法 URL
- `config.py` 的 `DATABASE_URL` 增加 `quote_plus` 密码编码，兼容 @/# 等特殊字符；`database.py` 统一改为引用该配置
- 新增 `SECRET_KEY` 启动校验，使用默认值时启动直接报错，防止带默认密钥部署

## 2026-09-11
- 修复删除有赞/有标签文章时的外键约束 500：`Article` 新增 `likes` 级联删除，`article_tag` 外键增加 `ondelete="CASCADE"`
- `delete_article` 手动清理标签关联（兼容已存在的数据库）

## 2026-09-12
- 评论增删后清除文章缓存，修复 comments_count 缓存旧值问题
- `SummarizeResponse` 新增 `hallucination_warning` 字段，幻觉警告不再被 Pydantic 静默丢弃
- RAG 启动时从 Chroma metadata 重建已上传文件集合，修复重启后重复上传产生重复 chunk

## 2026-09-13
- AI 模块测试重构为 fixture 版：移除模块级 TestClient，mock LLM 与 Redis，新增登录 fixture
- `conftest.py` 顶部设置 `TESTING=1`，`DATABASE_URL` 增加 sqlite 测试分支
- 测试不再依赖 MySQL 与真实 LLM Key，任意机器可跑

## 2026-09-14
- 注册接口欢迎邮件任务增加降级保护，Redis/Celery 不可用时注册仍正常返回 201
- JWT 库从 python-jose 迁移到 PyJWT（消除已知 CVE），`utcnow` 改为时区感知时间
- 登录接口新增防爆破锁定：连续失败 5 次锁定 10 分钟，计数存 Redis（INCR 原子操作 + TTL 自动过期）
- 认证依赖用户不存在时 404 改为 401，消除用户名枚举的信息泄露

## 2026-09-15
- 登录锁定增加进程内兜底：Redis 宕机时不再放行被锁账号（fail-closed），已知边界为多进程不共享
- Celery 增加 broker 连接超时与快速失败配置，修复 Redis 宕机时 kombu 无限重试阻塞请求数分钟的问题
- redis 客户端增加 socket 超时（3s）并关闭指数退避重试
- 修复 `broker_connection_max_retries=0` 语义陷阱（0 在 Celery 中为"无限重试"），改为 1 次即失败；无效配置 `broker_publish_retry` 替换为 `task_publish_retry=False`
- `/token` 接口补充失败计数，修复爆破者通过 OAuth2 登录端点绕过锁定的问题
