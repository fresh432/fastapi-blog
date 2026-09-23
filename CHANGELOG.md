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

## 2026-09-16
- RAG 引入 jieba 中文分词统一词表（建索引与查询共用），替换原空格分词，修复中文场景 BM25 关键词检索失效
- 新增中文分词单测与 BM25 命中/未命中对比测试；测试语料扩充至 3 篇（2 篇语料下 df=1 的词 idf 恒为 0 的小样本特性）

## 2026-09-17
- Agent 记忆序列化规范化：role 统一映射为 user/assistant/system/tool，不再存 LangChain 原始 type；assistant 消息完整保留 tool_calls(id+name+args)，tool 消息保留 tool_call_id 及 500 字结果摘要
- 新增 `_sanitize_history` 清洗不完整 tool 对（保存截断前后及加载重放时三处生效），防止截断后模型拿到半残工具记录而重复调用

## 2026-09-18
- 启动逻辑迁移至 lifespan，缓存预热失败降级跳过并记日志，不再阻塞启动
- 测试数据注入增加 SEED_TEST_DATA 开关，默认不注入假数据
- 删除 agent 模块无人调用的 `run_agent()` 等死代码，修正不规范 docstring

## 2026-09-19
- Docker 部署修正：dev compose 显式挂载 chroma_db 向量库目录（与 README 及 prod 配置对齐），nginx `http2` 迁移新指令写法（兼容 1.25+），.dockerignore 排除运行时数据目录
- SEED_TEST_DATA 配置收敛进 `config.py`，统一从 settings 读取（`.env` 写入即可生效）

## 2026-09-21
- 依赖治理：全部直接依赖 `==` 精确锁定，拆分 requirements-dev.txt（pytest 等测试依赖不进生产镜像）
- 移除无人引用的 passlib、jose 遗留的 cryptography 等无用依赖，补充 jieba

## 2026-09-22
- 测试补齐：新增点赞幂等、搜索分页边界、缓存命中/失效三组用例
- `conftest.py` 统一全局 mock Redis（实例方法级 patch，对所有 import 方式生效；测试可显式声明以控制返回值/断言调用），删除各文件分散 mock 与重复 fixture
- 修复测试路径缺少前导斜杠的问题
