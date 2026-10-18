"""
文章接口测试
"""

class TestArticleIdempotent:
    """文章接口测试"""

    def test_create_article(self, client, auth_headers):
        """文章创建测试"""
        r = client.post("/articles", json={"title": "文章测试", "content": "内容"}, headers=auth_headers)
        assert r.status_code == 201

    def test_delete_article(self, client, auth_headers):
        """删除文章测试"""
        r = client.post("/articles", json={"title": "文章测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]

        r = client.delete(f"/articles/{article_id}", headers=auth_headers)
        assert r.json()["message"] == "删除成功"

    def test_update_article(self, client, auth_headers):
        """文章更新测试"""
        r = client.post("/articles", json={"title": "文章测试1", "content": "内容1"}, headers=auth_headers)
        article_id = r.json()["id"]

        r = client.put(f"/articles/{article_id}", json={"title": "文章测试2", "content": "内容2"}, headers=auth_headers)
        assert r.json()["title"] == "文章测试2"
        assert r.json()["content"] == "内容2"

    def test_get_article(self, client, auth_headers):
        """获取单篇文章"""
        r = client.post("/articles", json={"title": "文章测试", "content": "内容"}, headers=auth_headers)
        article_id = r.json()["id"]
        r = client.get(f"/articles/{article_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["title"] == "文章测试"

    def test_create_article_unauthorized(self, client):
        """未登录创建文章返回401"""
        r = client.post("/articles", json={"title": "文章测试", "content": "内容"})
        assert r.status_code == 401

    def test_search_articles(self, client, auth_headers):
        """文章搜索测试"""
        client.post("/articles", json={"title": "test", "content": "内容"}, headers=auth_headers)
        r = client.get("/articles/search?q=test")
        assert r.status_code == 200
        assert r.json()["articles"][0]["title"] == "test"

    def test_list_articles(self, client, auth_headers):
        """文章列表测试"""
        for i in range(3):
            client.post("/articles", json={"title": f"文章测试{i}", "content": "内容"}, headers=auth_headers)
        r = client.get("/articles", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 3
