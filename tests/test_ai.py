"""
AI模块单元测试（fixture版 + mock外部依赖）
"""

import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_llm(monkeypatch):
    """Mock LLM 客户端, 避免调用真实API (需要LLM响应的测试显示使用) """
    def mock_get_llm_client():
        client = MagicMock()

        def mock_create(*args, **kwargs):
            response = MagicMock()
            message = MagicMock()

            # 判断是否摘要请求 (JSON格式输出)
            if kwargs.get("response_format") == {"type": "json_object"}:
                message.content = '{"title":"模拟标题","summary":"测试摘要","keywords":["测试"],"category":"后端"}'
            else:
                message.content = "这是一个模拟的LLM回复"

            response.choices = [MagicMock(message=message)]
            response.usage = None
            return response

        client.chat.completions.create = mock_create
        return client

    monkeypatch.setattr("app.routers.ai.get_llm_client", mock_get_llm_client)

@pytest.fixture(autouse=True)
def mock_redis(monkeypatch):
    """
    Mock Redis 客户端, 避免连接真实Redis
    autouse=True: 所有AI测试自动生效, 无需显示声明
    """
    mock_client = MagicMock()
    mock_client.get.return_value = None
    mock_client.setex.return_value = True
    mock_client.delete.return_value = True
    mock_client.scan_iter.return_value = []

    # 覆盖所有使用 redis_client 的地方
    monkeypatch.setattr("app.core.cache.redis_client", mock_client)
    monkeypatch.setattr("app.services.agent_memory.redis_client", mock_client)
    monkeypatch.setattr("app.services.chat_history.redis_client", mock_client)

@pytest.fixture
def auth_headers(client):
    client.post("/register", json={"username": "testuser", "password": "testpass123"})
    r = client.post("/login", json={"username": "testuser", "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

class TestAISummarize:
    """文章摘要接口测试"""

    def test_summarize_success(self, client, mock_llm):
        """正常摘要请求（mock LLM，不依赖真实API Key）"""
        response = client.post("/ai/summarize", json={
            "title": "FastAPI入门教程",
            "content": "FastAPI是一个现代、快速的Web框架，基于Python类型提示。它使用Starlette进行异步支持，使用Pydantic进行数据验证。",
            "max_length": 100
        })
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "keywords" in data
        assert "category" in data
        assert len(data["summary"]) <= 100

    def test_summarize_empty_content(self, client):
        """空内容应返回422（Pydantic校验阶段拦截，不走到LLM）"""
        response = client.post("/ai/summarize", json={
            "title": "测试",
            "content": "",
            "max_length": 100
        })
        assert response.status_code == 422  # Pydantic 校验失败

class TestAIChat:
    """LLM对话接口测试 (需登录) """

    def test_chat_unauthorized(self, client):
        """未登录应返回401"""
        response = client.post("/ai/chat", json={
            "messages": [{"role": "user", "content": "你好"}],
            "use_history": False
        })
        assert response.status_code == 401

    def test_chat_stream_unauthorized(self, client):
        """流式对话未登录应返回401"""
        response = client.post("/ai/chat/stream", json={
            "messages": [{"role": "user", "content": "你好"}],
            "use_history": False
        })
        assert response.status_code == 401

class TestAIRAG:
    """RAG知识库接口测试"""

    def test_ask_empty_messages(self, client, auth_headers):
        """空消息在 Pydantic 校验阶段拦截"""
        response = client.post("/ai/ask", json={"messages": []}, headers=auth_headers)
        assert response.status_code == 422

class TestAIAgent:
    """Agent智能体接口测试 (需登录) """

    def test_agent_unauthorized(self, client):
        """未登录应返回401"""
        response = client.post("/ai/agent", json={
            "messages": [{"role": "user", "content": "现在几点"}],
            "thread_id": "test_thread"
        })
        assert response.status_code == 401

