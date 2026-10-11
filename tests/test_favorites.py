"""
收藏接口测试: 幂等性 + 权限
"""

class TestFavoriteIdempotent:
    """收藏幂等测试"""

    def test_favorite_success(self, client, auth_headers):
        """正常收藏返回200和计数"""
        r = client.post("/articles", json={"title": "收藏测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        r = client.post(f"/favorites/{article_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["favorites_count"] == 1

    def test_favorite_twice_return_400(self, client, auth_headers):
        """重复收藏: 唯一约束触发IntegrityError, 返回400"""
        r = client.post("/articles", json={"title": "收藏测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.post(f"/favorites/{article_id}", headers=auth_headers)
        r = client.post(f"/favorites/{article_id}", headers=auth_headers)
        assert r.status_code == 400
        assert "已收藏" in r.json()["detail"]

    def test_unfavorite_success(self, client, auth_headers):
        """取消收藏正常, 计数减一"""
        r = client.post("/articles", json={"title": "收藏测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        client.post(f"/favorites/{article_id}", headers=auth_headers)
        r = client.delete(f"/favorites/{article_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["favorites_count"] == 0

    def test_unfavorite_default(self, client, auth_headers):
        r = client.post("/favorites/1", headers=auth_headers)
        assert r.status_code == 404

    def test_favorites_double_article(self, client, auth_headers):
        r = client.post("/articles", json={"title": "收藏测试1", "content": "内容"}, headers=auth_headers)
        article_1= r.json()["id"]
        r = client.post("/articles", json={"title": "收藏测试2", "content": "内容"}, headers=auth_headers)
        article_2 = r.json()["id"]

        client.post(f"/favorites/{article_1}", headers=auth_headers)
        r = client.post(f"/favorites/{article_2}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["favorites_count"] == 1


    def test_favorite_unauthorized(self, client):
        """未登录收藏返回401"""
        r = client.post(f"/favorites/1")
        assert r.status_code == 401


