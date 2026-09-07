"""
AI模块单元测试
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

class TestAISummarize:
    """文章摘要接口测试"""

    def test_summarize_success(self):
        """正常摘要请求"""
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

    def test_summarize_empty_content(self):
        """空内容应返回400"""
        response = client.post("/ai/summarize", json={
            "title": "测试",
            "content": "",
            "max_length": 100
        })
        assert response.status_code == 422  # Pydantic 校验失败

class TestAIChat:
    """LLM对话接口测试 (需登录) """

    def test_chat_unauthorized(self):
        """未登录应返回401"""
        response = client.post("/ai/chat", json={
            "messages": [{"role": "user", "content": "你好"}],
            "use_history": False
        })
        assert response.status_code == 401

    def test_chat_stream_unauthorized(self):
        """流式对话未登录应返回401"""
        response = client.post("/ai/chat/stream", json={
            "messages": [{"role": "user", "content": "你好"}],
            "use_history": False
        })
        assert response.status_code == 401

class TestAIRAG:
    """RAG知识库接口测试"""

    def test_ask_empty_messages(self):
        """空消息应返回400"""
        response = client.post("/ai/ask", json={
            "messages": []
        })
        assert response.status_code == 400

class TestAIAgent:
    """Agent智能体接口测试 (需登录) """

    def test_agent_unauthorized(self):
        """未登录应返回401"""
        response = client.post("/ai/agent", json={
            "messages": [{"role": "user", "content": "现在几点"}],
            "thread_id": "test_thread"
        })
        assert response.status_code == 401

