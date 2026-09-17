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

# LangChain type -> 标准role映射
_ROLE_MAP = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
    "tool": "tool",
}

TOOL_RESULT_MAX_LEN = 500 # tool结果摘要要最大长度, 防止工具输出撑爆上下文

def _serialize_message(msg) -> dict:
    """
    序列化消息为字典
    - role统一映射为 user/assistant/system/tool (不再直接存"human"/"ai")
    - assistant消息: 保留content + tool_calls(只留id和name, 证明调过哪些工具)
    - tool消息: 只保留tool_call_id + 结果摘要(截断, 防止超长工具输出占满Token)
    """
    try:
        # 兼容 LangChain Message 对象和已知序列化的dict
        if isinstance(msg, dict):
            msg_type = msg.get("type") or msg.get("role", "assistant")
            content = msg.get("content", "") or ""
            tool_calls = msg.get("tool_calls") or []
            tool_call_id = msg.get("tool_call_id", None)
        else:
            msg_type = getattr(msg, "type", "assistant")
            content = getattr(msg, "content", "") or ""
            tool_calls = getattr(msg, "tool_calls", None) or []
            tool_call_id = getattr(msg, "tool_call_id", None)

        role = _ROLE_MAP.get(msg_type, msg_type)

        if role == "assistant":
            result = {"role": "assistant", "content": content}
            if tool_calls:
                result["tool_calls"] = [
                    {"id": tc.get("id"), "name": tc.get("name"), "args": tc.get("args", {})}
                    for tc in tool_calls if isinstance(tc, dict)
                ]
            return result
        elif role == "tool":
            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": content[:TOOL_RESULT_MAX_LEN],
            }
        else:
            return {"role": role, "content": content}
    except Exception as e:
        logger.warning(f"消息序列化失败: {e}")
        return {"role": "assistant", "content": "[无法序列化的消息]"}

def _sanitize_history(history: List[Dict]) -> List[Dict]:
    """
    重放前清洗: 丢弃不完整的tool对
    取舍: 宁可丢上下文, 也不给模型半残的工具记录
    - assistant带tool_calls但后面没有对应tool结果 -> 整条丢弃
    - tool消息找不到发起它的assistant -> 孤儿消息, 丢弃
    """
    # 已有结果的tool_call_id集合
    answered_ids = {m.get("tool_call_id") for m in history if m.get("role") == "tool"}
    # assistant发起过的tool_call_id集合
    called_ids = set()
    for m in history:
        if m.get("role") == "assistant":
            for tc in m.get("tool_calls") or []:
                called_ids.add(tc.get("id"))

    cleaned = []
    for m in history:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            ids = {tc.get("id") for tc in m["tool_calls"]}
            if not ids <= answered_ids:
                logger.warning(f"丢弃不完整tool对: assistant的tool_calls {ids} 缺少结果")
                continue
        elif m.get("role") == "tool":
            if m.get("tool_call_id") not in called_ids:
                logger.warning(f"丢弃孤儿tool消息: tool_call_id={m.get('tool_call_id')}")
                continue
        cleaned.append(m)
    return cleaned

def save_memory(thread_id: str, messages:list):
    """保存 Agent 对话状态到 Redis (序列化规范化 + 清洗 + Token截断) """
    try:
        key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
        history = [_serialize_message(m) for m in messages[-MAX_HISTORY:]]

        # 丢弃不完整tool对, 防止截断把tool对拦截切断后存下半残记录
        history = _sanitize_history(history)

        # Token 截断: 从最早消息删除
        total_tokens = sum(_estimate_tokens(m.get("content", "")) for m in history)
        while total_tokens > MAX_TOKENS and len(history) > 1:
            removed = history.pop(0)
            total_tokens -= _estimate_tokens(removed.get("content", ""))

        # 截断可能再次切断tool对, 收尾再清洗一次
        history = _sanitize_history(history)

        redis_client.setex(key, TTL_SECONDS, json.dumps(history))
    except Exception as e:
        logger.error(f"保存Agent记忆失败: {e}")

def load_memory(thread_id: str) -> List[Dict[str, str]]:
    """从 Redis 加载 Agent 对话状态 (重放前清洗不完整tool对) """
    try:
        key = AGENT_MEMORY_KEY.format(thread_id=thread_id)
        data = redis_client.get(key)
        if data:
            return _sanitize_history(json.loads(data))
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