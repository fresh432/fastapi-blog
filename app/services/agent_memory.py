"""
Agent Memory 持久化：Redis 存储对话状态（增加 Token 估算截断）
"""

import json
import logging
from typing import List, Dict, Optional

from app.core.cache import redis_client

logger = logging.getLogger(__name__)
AGENT_MEMORY_KEY = "agent:thread:{thread_id}"
TTL_SECONDS = 86400 # 24小时过期
MAX_HISTORY = 20
MAX_TOKENS = 4000   # Agent 上下文更宽, Token 上限更高

def _estimate_tokens(text: str) -> int:
    """粗略估算 Token 数 (同 chat_history.py) """
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len([w for w in text.split() if w.isascii()])
    return chinese_chars + int(english_words * 1.5)

def _serialize_message(msg) -> dict:
    """序列化消息为字典 (带异常保护) """
    try:
        if hasattr(msg, "model_dump"):
            d = msg.model_dump()
        elif hasattr(msg, "content"):
            d = {
                "role": getattr(msg, "type", "assistant"),
                "content": msg.content,
            }
        else:
            d = {"role": "assistant", "content": str(msg)}

        # 只保留 role 和 content 用于 Token 估算
        return {"role": d.get("role", "assistant"), "content": d.get("content", "")}
    except Exception as e:
        logger.warning(f"消息序列化失败: {e}")
        return {"role": "assistant", "content": "[无法序列化的消息]"}

def save_memory(thread_id: str, messages:list):
    """保存 Agent 对话状态到 Redis (带 Token 截断) """
    try:
        key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
        history = [_serialize_message(m) for m in messages[-MAX_HISTORY:]]

        # Token 截断: 从最早消息删除
        total_tokens = sum(_estimate_tokens(m.get("content", "")) for m in history)
        while total_tokens > MAX_TOKENS and len(history) > 1:
            removed = history.pop(0)
            total_tokens -= _estimate_tokens(removed.get("content", ""))

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