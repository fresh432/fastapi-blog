"""
Agent Memory 持久化：Redis 存储对话状态
"""

import json
from typing import List, Dict, Optional

from app.core.cache import redis_client


AGENT_MEMORY_KEY = "agent:thread:{thread_id}"
TTL_SECONDS = 86400 # 24小时过期

def _serialize_message(msg) -> dict:
    """序列化消息为字典"""
    if hasattr(msg, "model_dump"):
        return msg.model_dump()
    elif hasattr(msg, "content"):
        return {
            "role": getattr(msg, "type", "assistant"),
            "content": msg.content,
        }
    return {"role": "assistant", "content": str(msg)}

def save_memory(thread_id: str, messages:list):
    """保存 Agent 对话状态到 Redis"""
    key = AGENT_MEMORY_KEY.format(thread_id=thread_id)

    # 只保存最近 20 条消息 (防止过长)
    history = [_serialize_message(m) for m in messages[-20:]]

    redis_client.setex(key, TTL_SECONDS, json.dumps(history))

def load_memory(thread_id: str) -> List[Dict[str, str]]:
    """从 Redis 加载 Agent 对话状态"""
    key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
    data = redis_client.get(key)

    if data:
        return json.loads(data)
    return []

def clear_memory(thread_id: str):
    """清空指定 thread 的记忆"""
    key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
    redis_client.delete(key)