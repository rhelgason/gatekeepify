class TestErrorResponses:
    def test_404_has_consistent_shape(self, client, seeded_db, auth_headers):
        resp = client.get("/gatekeep/artist/nonexistent", headers=auth_headers)
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "detail" in data
        assert data["error"] == "http_error"

    def test_401_has_consistent_shape(self, client, seeded_db):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401
        data = resp.json()
        assert "error" in data
        assert "detail" in data
        assert data["error"] == "http_error"

    def test_422_validation_error_has_consistent_shape(self, client, seeded_db, auth_headers):
        resp = client.get("/search/artists", headers=auth_headers)
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert "detail" in data
        assert data["error"] == "validation_error"

    def test_400_has_consistent_shape(self, client, seeded_db, auth_headers):
        resp = client.post(
            "/backfill/upload",
            headers=auth_headers,
            files={"file": ("data.txt", b"not a zip", "text/plain")},
        )
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data
        assert "detail" in data

    def test_health_unaffected(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["checks"]["database"] == "ok"
