from openai import OpenAI
from app.core.config import settings

_client = None

def get_llm_client() -> OpenAI:
    """获取LLM客户端单例"""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            timeout=settings.LLM_TIMEOUT,
        )
    return _client