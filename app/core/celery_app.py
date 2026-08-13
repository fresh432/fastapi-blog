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

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)