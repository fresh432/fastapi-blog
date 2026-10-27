"""
缓存测试: 命中/未命中/失效
"""

import json

class TestArticleCache:
    """文章详情缓存测试"""

    def test_cache_miss_then_set(self, client, auth_headers, mock_cache_redis):
        """首次GET缓存未命中: 走库并写入缓存(setex被调用)"""
        r = client.post("/articles", json={"title": "缓存测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        r = client.get(f"/articles/{article_id}")
        assert r.status_code == 200
        assert mock_cache_redis.get(f"fastapi:article:{article_id}") is not None

    def test_cache_hit_returns_cached(self, client, auth_headers, mock_cache_redis):
        """缓存命中: 直接返回缓存内容"""
        r = client.post("/articles", json={"title": "缓存测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.get(f"/articles/{article_id}")
        article = json.loads(mock_cache_redis.get(f"fastapi:article:{article_id}"))
        article["title"] = "假标题"
        mock_cache_redis.set(f"fastapi:article:{article_id}", json.dumps(article))
        r = client.get(f"/articles/{article_id}")
        assert r.json()["title"] == "假标题"

    def test_cache_invalidate_on_update(self, client, auth_headers, mock_cache_redis):
        """更新文章后缓存被删除 (delete被调用, key正确)"""
        r = client.post("/articles", json={"title": "缓存测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.get(f"/articles/{article_id}")
        assert mock_cache_redis.get(f"fastapi:article:{article_id}") is not None
        client.put(f"/articles/{article_id}", json={"title": "新标题"}, headers=auth_headers)
        assert mock_cache_redis.get(f"fastapi:article:{article_id}") is None
