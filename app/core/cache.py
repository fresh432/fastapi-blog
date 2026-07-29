"""
Redis缓存配置
"""

import os
from dotenv import load_dotenv
import redis
import json
import random
from typing import Optional, Any

load_dotenv()

redis_password = os.getenv("REDIS_PASSWORD", "")

# Redis连接
redis_client = redis.Redis(
    host='192.168.60.128',
    port=6379,
    password=redis_password,
    db=0,
    decode_responses=True
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