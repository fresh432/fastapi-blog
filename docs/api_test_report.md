# FastAPI-Blog 接口全量测试报告

## 一、测试环境
| 项目      | 版本/配置                  |
| ------- | ---------------------- |
| Python  | 3.11+                  |
| FastAPI | 0.111+                 |
| 数据库     | MySQL 8.0 (Docker)     |
| 缓存      | Redis 7 (Docker)       |
| 向量库     | Chroma (本地持久化)         |
| 测试时间    | 2026-08-14             |
| 测试方式    | Swagger UI + curl 手工验证 |

## 二、测试范围
| 模块     |   接口数  |         状态        |
| ------ | :----: | :---------------: |
| 用户模块   |    5   |        ✅ 通过       |
| 文章模块   |    7   | ✅ 通过（发现1个bug，已修复） |
| 分类模块   |    4   |        ✅ 通过       |
| 评论模块   |    3   |        ✅ 通过       |
| 标签模块   |    4   |        ✅ 通过       |
| 点赞模块   |    3   |        ✅ 通过       |
| AI 模块  |    7   |        ✅ 通过       |
| **合计** | **33** |      **全部通过**     |

## 三、测试用例详情

### 1. 用户模块
| 接口       | 方法   | 路径          | 测试结果 | 备注                          |
| -------- | ---- | ----------- | :--: | --------------------------- |
| 注册       | POST | `/register` |   ✅  | username/password校验，重复注册400 |
| JSON登录   | POST | `/login`    |   ✅  | 返回access\_token             |
| OAuth2登录 | POST | `/token`    |   ✅  | form-data，返回bearer token    |
| 获取资料     | GET  | `/users/me` |   ✅  | 依赖注入获取当前用户                  |
| 更新资料     | PUT  | `/users/me` |   ✅  | avatar/bio可选更新              |

### 2. 文章模块
| 接口   | 方法     | 路径                 | 测试结果 | 备注                                    |
| ---- | ------ | ------------------ | :--: | ------------------------------------- |
| 创建   | POST   | `/articles`        |   ✅  | 支持published/draft状态                   |
| 列表   | GET    | `/articles`        |   ✅  | skip/limit/status筛选+Redis缓存           |
| 草稿列表 | GET    | `/articles/drafts` |   ✅  | 仅返回当前用户草稿                             |
| 搜索   | GET    | `/articles/search` |   ✅  | LIKE模糊搜索，限流10次/分钟                     |
| 单篇   | GET    | `/articles/{id}`   |   ✅  | 含tags/likes\_count/comments\_count+缓存 |
| 更新   | PUT    | `/articles/{id}`   |   ✅  | **修复前：author可修改导致权限绕过**               |
| 删除   | DELETE | `/articles/{id}`   |   ✅  | 作者权限校验+缓存清除                           |

### 3. 分类模块
| 接口   | 方法     | 路径                          | 测试结果 | 备注                            |
| ---- | ------ | --------------------------- | :--: | ----------------------------- |
| 创建   | POST   | `/categories`               |   ✅  |                               |
| 列表   | GET    | `/categories`               |   ✅  | N+1查询已优化（outerjoin+group\_by） |
| 文章列表 | GET    | `/categories/{id}/articles` |   ✅  |                               |
| 删除   | DELETE | `/categories/{id}`          |   ✅  | 关联文章category\_id置NULL         |

### 4. 评论模块
| 接口 | 方法     | 路径                       | 测试结果 | 备注           |
| -- | ------ | ------------------------ | :--: | ------------ |
| 创建 | POST   | `/comments`              |   ✅  |              |
| 列表 | GET    | `/comments/article/{id}` |   ✅  | skip/limit分页 |
| 删除 | DELETE | `/comments/{id}`         |   ✅  | 只能删除自己的评论    |

### 5. 标签模块
| 接口   | 方法   | 路径                                 | 测试结果 | 备注 |
| ---- | ---- | ---------------------------------- | :--: | -- |
| 创建   | POST | `/tags`                            |   ✅  |    |
| 列表   | GET  | `/tags`                            |   ✅  |    |
| 关联文章 | POST | `/tags/{article_id}/tags/{tag_id}` |   ✅  |    |
| 标签文章 | GET  | `/tags/{tag_id}/articles`          |   ✅  |    |

### 6. 点赞模块
| 接口   | 方法     | 路径                          | 测试结果 | 备注             |
| ---- | ------ | --------------------------- | :--: | -------------- |
| 点赞   | POST   | `/likes/{article_id}`       |   ✅  | 重复点赞400，清除文章缓存 |
| 取消点赞 | DELETE | `/likes/{article_id}`       |   ✅  | 未点赞404，清除文章缓存  |
| 计数   | GET    | `/likes/{article_id}/count` |   ✅  |                |

### 7. AI 模块
| 接口      | 方法   | 路径                 | 测试结果 | 备注                                       |
| ------- | ---- | ------------------ | :--: | ---------------------------------------- |
| 对话      | POST | `/ai/chat`         |   ✅  | 支持历史记录，use\_history/clear\_history       |
| 流式对话    | POST | `/ai/chat/stream`  |   ✅  | SSE格式，data:前缀                            |
| 文章摘要    | POST | `/ai/summarize`    |   ✅  | 结构化JSON输出，Pydantic约束                     |
| 文档上传    | POST | `/ai/upload`       |   ✅  | **修复前：重复file.read()导致内容为空**；限制txt/md/5MB |
| 知识库问答   | POST | `/ai/ask`          |   ✅  | Hybrid Search，空检索降级为直接LLM                |
| Agent   | POST | `/ai/agent`        |   ✅  | **修复前：clear\_memory参数错误**；支持thread\_id记忆 |
| Agent流式 | POST | `/ai/agent/stream` |   ✅  | SSE，实时返回工具调用过程                           |

## 四、发现的问题与修复
| # | 问题                              | 文件                    | 影响                | 修复方案                                 |
| - | ------------------------------- | --------------------- | ----------------- | ------------------------------------ |
| 1 | `/ai/upload` 重复 `file.read()`   | `routers/ai.py`       | 上传文件内容为空          | 删除第二次 `file.read()`                  |
| 2 | `/ai/agent` `clear_memory` 参数错误 | `routers/ai.py`       | 清除记忆时报错           | `request` → `request.thread_id`      |
| 3 | RRF 融合遍历对象错误                    | `services/rag.py`     | BM25完全失效，退化为纯向量检索 | `vector_results` → `keyword_results` |
| 4 | Chroma 文档键名错误                   | `services/rag.py`     | BM25索引构建失败        | `"document"` → `"documents"`         |
| 5 | 文章更新权限绕过                        | `routers/articles.py` | 修改author后文章归属他人   | `update_data.pop("author", None)`    |

## 五、测试结论
- **全部 33 个接口测试通过**
- **5 个bug全部修复并验证**
- **权限安全：** 文章操作校验作者身份，更新禁止修改author
- **性能：** Redis缓存+空值防穿透+随机过期防雪崩，N+1查询已优化
- **AI模块：** 原生API→RAG知识库→Agent智能体完整链路可用
- **部署：** Docker Compose一键启动（Web+MySQL+Redis）

