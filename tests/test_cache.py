"""
缓存测试: 命中/未命中/失效
注意: mock的是app.core.cache.redis_client, 因为cache模块内的函数
(get_cache/set_cache/delete_cache)在调用时才读取这个模块级全局变量
"""

import json

class TestArticleCache:
    """文章详情缓存测试"""

    def test_cache_miss_then_set(self, client, auth_headers, mock_cache_redis):
        """首次GET缓存未命中: 走库并写入缓存(setex被调用)"""
        r = client.post("/articles", json={"title": "缓存测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        mock_cache_redis.get.return_value = None
        r = client.get(f"/articles/{article_id}")
        assert r.status_code == 200
        assert mock_cache_redis.setex.called    # 写入了缓存

    def test_cache_hit_returns_cached(self, client, auth_headers, mock_cache_redis):
        """缓存命中: 直接返回缓存内容 (用假标题证明没走库)"""
        r = client.post("/articles", json={"title": "缓存测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        mock_cache_redis.get.return_value = json.dumps({
            "id": article_id, "title": "来自缓存的假标题", "content": "x",
            "author": "testuser", "category_id": None, "tags": [],
            "likes_count": 0, "comments_count": 0, "created_at": "2026-09-22T12:00:00",
        })
        r = client.get(f"/articles/{article_id}")
        assert r.json()["title"] == "来自缓存的假标题"  # 证明走了缓存路径

    def test_cache_invalidate_on_update(self, client, auth_headers, mock_cache_redis):
        """更新文章后混村被删除 (delete被调用, key正确)"""
        r = client.post("/articles", json={"title": "缓存测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.put(f"/articles/{article_id}", json={"title": "新标题"}, headers=auth_headers)
        mock_cache_redis.delete.assert_any_call(f"fastapi:article:{article_id}")
