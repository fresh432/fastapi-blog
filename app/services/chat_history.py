import json
from typing import List, Dict
from app.core.cache import redis_client # 复用现有 Redis 客户端

CHAT_HISTORY_KEY = "chat:history:{user_id}"
MAX_HISTORY_ROUNDS = 10 # 保留最近 10 轮
TTL_SECONDS = 3600 # 1 小时过期

def get_history(user_id: str) -> List[Dict[str, str]]:
    """获取用户对话历史"""
    key = CHAT_HISTORY_KEY.format(user_id=user_id)
    data = redis_client.get(key)
    if data:
        return json.loads(data)
    return []

def add_to_history(user_id: str, role: str, content: str):
    """添加消息到历史"""
    key = CHAT_HISTORY_KEY.format(user_id=user_id)
    history = get_history(user_id)

    history.append({"role": role, "content": content})

    # 只保留最近 MAX_HISTORY_ROUNDS 轮 (每轮 2 条消息)
    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history = history[-MAX_HISTORY_ROUNDS * 2:]

    redis_client.setex(key, TTL_SECONDS, json.dumps(history))

def clear_history(user_id: str):
    """清空对话历史"""
    key = CHAT_HISTORY_KEY.format(user_id=user_id)
    redis_client.delete(key)
