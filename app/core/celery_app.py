from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

redis_password = os.getenv("REDIS_PASSWORD", "")

celery_app = Celery(
    "fastapi_blog",
    broker=f"redis://:{redis_password}@192.168.60.128:6379/1",
    backend=f"redis://:{redis_password}@192.168.60.128:6379/2",
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
)