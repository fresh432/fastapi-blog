"""
Redis缓存配置
"""

import redis
import json
import random
import logging
from typing import Optional, Any
from redis.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff

from app.core.config import settings

logger = logging.getLogger(__name__)

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
    """读缓存; Redis不可用时降级为未命中(走数据库)并记日志"""
    try:
        value = redis_client.get(key)
        return value
    except Exception as e:
        logger.warning(f"缓存读取失败(降级为未命中, 走数据库): {key}, 原因: {e}")
        return None

def set_cache(key: str, value: str, base_expire: int = 300):
    """写缓存; Redis不可用时降级跳过并记日志"""
    try:
        expire = base_expire + random.randint(0, 60)
        redis_client.setex(key, expire, value)
    except Exception as e:
        logger.warning(f"缓存写入失败(已跳过): {key}, 原因: {e}")

def set_null_cache(key: str, expire: int = 60):
    """写空值缓存防穿透; Redis不可用时降级跳过并记日志"""
    try:
        redis_client.setex(key, expire, "__NULL__")
    except Exception as e:
        logger.warning(f"空值缓存写入失败(已跳过): {key}, 原因: {e}")

def is_null_value(value: str) -> bool:
    """判断是否为空值缓存"""
    return value == "__NULL__"

def delete_cache(key: str):
    """删除缓存; Redis不可用时降级跳过并记日志(缓存失效失败不影响主流程)"""
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning(f"缓存删除失败(已降级): {key}, 原因: {e}")


def delete_cache_pattern(pattern: str):
    """按前缀批量删除; Redis不可用时降级跳过并记日志"""
    try:
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)
    except Exception as e:
        logger.warning(f"缓存批量删除失败(已降级): {pattern}, 原因: {e}")