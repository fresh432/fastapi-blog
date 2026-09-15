"""
Redis缓存配置
"""

import redis
import json
import random
from typing import Optional, Any
from redis.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff

from app.core.config import settings

# Redis连接（从统一配置读取）
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD,
    db=settings.REDIS_DB,
    decode_responses=True,
    socket_timeout=3,           # 读写超时, 防止socket层无限等待
    socket_connect_timeout=3,   # 连接超时, Redis宕机时快速失败
    # 缓存/登录锁定属快速路径, 失败应立刻抛异常走降级, 不应原地退避等待
    retry=Retry(ExponentialWithJitterBackoff(base=0.5, cap=2), retries=0),
)

def get_cache(key: str) -> Optional[str]:
    """获取缓存"""
    return redis_client.get(key)

def set_cache(key: str, value: str, base_expire: int = 300):
    """
    设置缓存，随机过期时间防止雪崩
    """
    expire = base_expire + random.randint(0, 60)
    redis_client.setex(key, expire, value)

def set_null_cache(key: str, expire: int = 60):
    """缓存空值, 防止穿透"""
    redis_client.setex(key, expire, "__NULL__")

def is_null_value(value: str) -> bool:
    """判断是否为空值缓存"""
    return value == "__NULL__"

def delete_cache(key: str):
    """删除缓存"""
    redis_client.delete(key)

def delete_cache_pattern(pattern: str):
    """按模式删除缓存"""
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)