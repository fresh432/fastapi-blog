"""
LLM 客户端封装：单例 + 指数退避重试 + 模型降级
"""

from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

_client = None
_fallback_client = None

def get_llm_client() -> OpenAI:
    """获取LLM客户端单例（主模型：DeepSeek）"""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            timeout=settings.LLM_TIMEOUT,
            max_retries=0, # 关闭底层重试, 统一用 tenacity 管理
        )
    return _client

def get_fallback_client() -> OpenAI:
    """获取备用LLM客户端（降级模型：通义千问）"""
    global _fallback_client
    if _fallback_client is None:
        _fallback_client = OpenAI(
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=settings.QW_API_KEY,
            model="qwen-turbo",
            timeout=settings.LLM_TIMEOUT,
            max_retries=0,
        )

# 可重试异常: 网络层/限流问题, 重试可能恢复
RETRYABLE_ERRORS = (
    APITimeoutError,        # 读取超时
    APIConnectionError,     # 连接失败 (DNS/TCP层)
    RateLimitError,         # 429限流
)

# 不可重试：AuthenticationError(401)、PermissionDeniedError(403)、BadRequestError(400)

@retry(
    stop=stop_after_attempt(3),                         # 最多重试3次 (共4次请求)
    wait=wait_exponential(multiplier=1, min=2, max=10), # 指数退避: 2s, 4s, 8s...
    retry=retry_if_exception_type(RETRYABLE_ERRORS),
    reraise=True,                                       # 最终失败时抛出原始异常
)
def chat_with_retry(*args, **kwargs):
    """带指数退避重试的LLM对话调用"""
    client = get_llm_client()
    return client.chat.completions.create(*args, **kwargs)

def chat_with_fallback(*args, **kwargs):
    """
    带模型降级的LLM对话调用
    主模型失败3次后, 自动切换到备用模型
    """
    try:
        return chat_with_retry(*args, **kwargs)
    except Exception as e:
        # 主模型失败, 降级到备用模型
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"主模型调用失败, 降级到备用模型: {e}")

        client = get_fallback_client()
        return client.chat.completions.create(*args, **kwargs)