"""
搜索接口测试: 前缀匹配 + 分页正确性
"""

def _create_articles(client, auth_headers, count=5):
    for i in range(count):
        client.post("/articles", json={"title": f"FastAPI教程第{i}篇", "content": "内容"}, headers=auth_headers)

class TestSearchPagination:
    """搜索分页测试"""

    def test_search_total_and_page_size(self, client, auth_headers):
        """total正确, 每页条数正确"""
        _create_articles(client, auth_headers)

        r = client.get("/articles/search?q=FastAPI&skip=0&limit=2")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        assert len(data["articles"]) == 2

    def test_search_pages_no_overlap(self, client, auth_headers):
        """翻页不重复不遗漏"""
        _create_articles(client, auth_headers)

        ids = set()
        for skip in (0, 2, 4):
            r = client.get(f"/articles/search?q=FastAPI&skip={skip}&limit=2")
            for a in r.json()["articles"]:
                assert a["id"] not in ids   # 无重复
                ids.add(a["id"])
        assert len(ids) == 5    # 无遗漏

    def test_search_prefix_match(self, client, auth_headers):
        """前缀匹配生效: 匹配标题前缀, 不匹配中间字"""
        client.post("/articles", json={"title": "Redis入门", "content": "内容"}, headers=auth_headers)

        r1 = client.get("articles/search?q=Redis")
        assert r1.json()["total"] == 1
        r2 = client.get("articles/search?q=Python入门")
        assert r2.json()["total"] == 0