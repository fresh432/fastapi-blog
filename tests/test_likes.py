"""
点赞接口测试: 幂等性 + 权限
"""

class TestLikeIdempotent:
    """点赞幂等测试 (唯一约束兜底)"""

    def test_like_success(self, client, auth_headers):
        """正常点赞返回200和计数"""
        r = client.post("/articles", json={"title": "点赞测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        r = client.post(f"/likes/{article_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["likes_count"] == 1

    def test_like_twice_returns_400(self, client, auth_headers):
        """重复点赞: 唯一约束触发IntegrityError, 返回400"""
        r = client.post("/articles", json={"title": "点赞测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.post(f"/likes/{article_id}", headers=auth_headers)
        r = client.post(f"/likes/{article_id}", headers=auth_headers)
        assert r.status_code == 400
        assert "已点赞" in r.json()["detail"]

    def test_unlike_success(self, client, auth_headers):
        """取消点赞正常, 计数减一"""
        r = client.post("/articles", json={"title": "点赞测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.post(f"/likes/{article_id}", headers=auth_headers)
        r = client.delete(f"likes/{article_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["likes_count"] == 0

    def test_like_unauthorized(self, client):
        """未登录点赞返回401"""
        r = client.post("/likes/1")
        assert r.status_code == 401