from celery import Celery
from urllib.parse import quote_plus

from app.core.config import settings

redis_host = settings.REDIS_HOST
password = settings.REDIS_PASSWORD
redis_password = quote_plus(password)

celery_app = Celery(
    "fastapi_blog",
    broker=f"redis://:{redis_password}@{redis_host}:6379/1",
    backend=f"redis://:{redis_password}@{redis_host}:6379/2",
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
)