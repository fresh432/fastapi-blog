from celery import Celery
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus

load_dotenv()

redis_host = os.getenv("REDIS_HOST", "localhost")
password = os.getenv("DB_PASSWORD")
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