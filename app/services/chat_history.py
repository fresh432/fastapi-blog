import json
from typing import List, Dict
from app.core.cache import redis_client # 复用现有 Redis 客户端

CHAT_HISTORY_KEY = "chat:history:{user_id}"
MAX_HISTORY_ROUNDS = 10 # 保留最近 10 轮
MAX_TOKENS = 3000 # Token 上限 (粗略估算)
TTL_SECONDS = 3600 # 1 小时过期

def _estimate_tokens(text: str) -> int:
    """
    粗略估算 Token 数
    - 中文字符: 1 字 ≈ 1 Token
    - 英文字符: 按空格分词后 * 1.5
    - 标点符号: 忽略或按字符计
    """
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    english_words = len([w for w in text.split() if w.isascii()])
    return chinese_chars + int(english_words * 1.5)

def _estimate_messages_tokens(messages: List[Dict[str, str]]) -> int:
    """估算消息列表总 Token 数"""
    total = 0
    for msg in messages:
        total += _estimate_tokens(msg.get("content", ""))
        # 角色字段也占少量 Token
        total += _estimate_tokens(msg.get("role", ""))
    return total

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

    # 按 Token 截断
    # 保留系统消息(如果有), 从最早的 user/assistant 开始删
    while _estimate_messages_tokens(history) > MAX_TOKENS and len(history) > 1:
        # 找到第一个非 system 消息删除
        for i, msg in enumerate(history):
            if msg.get("role") != "system":
                history.pop(i)
                break
        else:
            # 全是 system 消息, 删最早的
            history.pop(0)

    # 兜底：按条数截断（每轮 2 条消息）
    if len(history) > MAX_HISTORY_ROUNDS * 2:
        history = history[-MAX_HISTORY_ROUNDS * 2:]

    redis_client.setex(key, TTL_SECONDS, json.dumps(history))

def clear_history(user_id: str):
    """清空对话历史"""
    key = CHAT_HISTORY_KEY.format(user_id=user_id)
    redis_client.delete(key)
