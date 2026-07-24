"""
Redis缓存配置
"""

import redis
import json
from typing import Optional, Any

# Redis连接
redis_client = redis.Redis(
    host='192.168.60.128',
    port=6379,
    password='12345dcb@',
    db=0,
    decode_responses=True
)

def get_cache(key: str) -> Optional[str]:
    """获取缓存"""
    return redis_client.get(key)

def set_cache(key: str, value: str, expire: int = 300):
    """设置缓存, 默认5分钟过期"""
    redis_client.setex(key, expire, value)

def delete_cache(key: str):
    """删除缓存"""
    redis_client.delete(key)

def delete_cache_pattern(pattern: str):
    """按模式删除缓存"""
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)