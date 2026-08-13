"""
Agent Memory 持久化：Redis 存储对话状态
"""

import json
import logging
from typing import List, Dict, Optional

from app.core.cache import redis_client

logger = logging.getLogger(__name__)
AGENT_MEMORY_KEY = "agent:thread:{thread_id}"
TTL_SECONDS = 86400 # 24小时过期
MAX_HISTORY = 20

def _serialize_message(msg) -> dict:
    """序列化消息为字典 (带异常保护) """
    try:
        if hasattr(msg, "model_dump"):
            return msg.model_dump()
        elif hasattr(msg, "content"):
            return {
                "role": getattr(msg, "type", "assistant"),
                "content": msg.content,
            }
        return {"role": "assistant", "content": str(msg)}
    except Exception as e:
        logger.warning(f"消息序列化失败: {e}")
        return {"role": "assistant", "content": "[无法序列化的消息]"}

def save_memory(thread_id: str, messages:list):
    """保存 Agent 对话状态到 Redis (带异常捕获) """
    try:
        key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
        history = [_serialize_message(m) for m in messages[-MAX_HISTORY:]]
        redis_client.setex(key, TTL_SECONDS, json.dumps(history))
    except Exception as e:
        logger.error(f"保存Agent记忆失败: {e}")

def load_memory(thread_id: str) -> List[Dict[str, str]]:
    """从 Redis 加载 Agent 对话状态 (带异常捕获) """
    try:
        key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
        data = redis_client.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.error(f"加载Agent记忆失败: {e}")
    return []

def clear_memory(thread_id: str):
    """清空指定 thread 的记忆 (带异常捕获) """
    try:
        key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
        redis_client.delete(key)
    except Exception as e:
        logger.error(f"清空Agent记忆失败: {e}")