from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "fastapi_blog",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks"]
)

"""
并发模型选择说明：
- 默认 prefork（进程池）：适合 CPU 密集型 + 隔离性要求高的任务
  如文章摘要、数据统计。进程崩溃互不影响，可利用多核。
- 可选 gevent/eventlet（协程池）：适合纯 IO 密集型短任务
  如批量 HTTP 请求。启动：celery worker -P gevent -c 1000
- 不选线程池的原因：Python GIL 限制，多线程无法利用多核，
  且线程切换在 CPU 密集型场景下反而增加开销。
- Web 层现状：FastAPI 同步路由 + SQLAlchemy 同步版，
  FastAPI 自动将同步路由扔到线程池执行，当前并发量下性能足够。
  未来可迁移到 SQLAlchemy 2.0 async + 异步路由。
"""

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # Redis宕机时快速失败, 由调用方try/except降级, 不阻塞请求线程
    broker_connection_timeout=2,        # 连接broker超时2秒
    broker_connection_max_retries=0,    # 连接失败不重试(kombu默认递增高频重试, 可阻塞数分钟)
    broker_publish_retry=False,         # 发布失败不自动重试, 立即抛异常
    broker_transport_options={          # kombu传输层(Redis)socket超时
        "socket_connect_timeout": 2,
        "socket_timeout": 2,
    }
)