def test_list_articles(client, db):
    from app.models.article import Article
    fake_article = Article(title="Test", content="Test")
    db.add(fake_article)
    db.commit()

    response = client.get("/articles")
    assert response.status_code == 200

def test_create_article_unauthorized(client):
    response = client.post("/articles", json={"title": "Test", "content": "Test"})
    assert response.status_code == 401

def test_search_articles(client):
    response = client.get("/articles/search?q=test")
    assert response.status_code == 200