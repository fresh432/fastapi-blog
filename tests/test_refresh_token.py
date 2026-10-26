"""
刷新令牌测试
"""

class TestRefreshToken:
    """刷新令牌测试"""

    def _get_refresh_token(self, client):
        client.post("/register", json={"username": "testuser", "password": "testpass123"})
        r = client.post("/login", json={"username": "testuser", "password": "testpass123"})
        return {"auth-token": f"Bearer {r.json()['refresh_token']}"}

    def test_refresh_success(self, client):
        """刷新成功拿到新 token 对"""
        refresh_token = self._get_refresh_token(client)
        r = client.post("/token/refresh", headers=refresh_token)

        assert r.status_code == 200
        assert "access_token" in r.json()
        assert "refresh_token" in r.json()

    def test_refresh_old_rt_rejected(self, client):
        """旧 RT 重放 -> 拒绝"""
        refresh_token = self._get_refresh_token(client)
        client.post("/token/refresh", headers=refresh_token)
        r = client.post("/token/refresh", headers=refresh_token)

        assert r.status_code == 401
        assert "刷新令牌无效" in r.json()["detail"]

    def test_refresh_invalid_rt_401(self, client):
        """过期/伪造 RT -> 401"""
        r = client.post("/token/refresh", headers={"auth-token": "Bearer invalidtoken"})

        assert r.status_code == 401
        assert "刷新令牌无效" in r.json()["detail"]

    def test_refresh_missing_token_401(self, client):
        """未带 token -> 401"""
        r = client.post("/token/refresh", headers={"auth-token": "Bearer "})

        assert r.status_code == 401
        assert "刷新令牌为空" in r.json()["detail"]

    def test_refresh_access_token_rejected(self, client, auth_headers):
        """用 AT 请求 RT -> 401"""
        r = client.post("/token/refresh", headers={"auth-token": f"{auth_headers['Authorization']}"})
        assert r.status_code == 401
        assert "令牌类型错误" in r.json()["detail"]

    def test_refresh_after_logout_rejected(self, client):
        """登出后用旧 RT 刷新 -> 401"""
        refresh_token = self._get_refresh_token(client)
        client.post("/logout", headers=refresh_token)
        r = client.post("/token/refresh", headers=refresh_token)

        assert r.status_code == 401
        assert "刷新令牌无效" in r.json()["detail"]