import os
os.environ["TESTING"] = "1"
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.core.cache import redis_client
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# 测试数据库 (内存SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def mock_cache_redis(monkeypatch):
    """全局 mock Redis：patch 实例方法, 对所有 import 方式生效"""
    mock = MagicMock()
    mock.get.return_value = None
    mock.scan_iter.return_value = iter([])
    monkeypatch.setattr(redis_client, "ping", mock.ping)
    monkeypatch.setattr(redis_client, "get", mock.get)
    monkeypatch.setattr(redis_client, "setex", mock.setex)
    monkeypatch.setattr(redis_client, "set", mock.set)
    monkeypatch.setattr(redis_client, "delete", mock.delete)
    monkeypatch.setattr(redis_client, "scan_iter", mock.scan_iter)
    return mock

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    """注册+登录, 返回认证头 (各测试文件共用)"""
    client.post("/register", json={"username": "testuser", "password": "testpass123"})
    r = client.post("/login", json={"username": "testuser", "password": "testpass123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
