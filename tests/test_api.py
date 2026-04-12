"""
Tests for app.api.session — FastAPI session bootstrap endpoints.

Uses httpx.AsyncClient with ASGITransport — no real network calls.
Tests use anonymous sessions (user_id=null) so no disk writes occur.
"""
import pytest


class TestHealthEndpoint:
    async def test_health_returns_200(self, api_client):
        resp = await api_client.get("/health")
        assert resp.status_code == 200

    async def test_health_returns_ok_status(self, api_client):
        resp = await api_client.get("/health")
        body = resp.json()
        assert body["status"] == "ok"
        assert "service" in body


class TestCreateSession:
    async def test_create_session_returns_200(self, api_client):
        resp = await api_client.post("/session/create", json={})
        assert resp.status_code == 200

    async def test_create_session_returns_session_id(self, api_client):
        resp = await api_client.post("/session/create", json={})
        body = resp.json()
        assert "session_id" in body
        assert len(body["session_id"]) > 0

    async def test_create_session_status_is_initializing(self, api_client):
        resp = await api_client.post("/session/create", json={})
        body = resp.json()
        assert body["status"] == "initializing"

    async def test_create_session_adult_mode_is_false_by_default(self, api_client):
        resp = await api_client.post("/session/create", json={})
        body = resp.json()
        assert body["adult_mode"] is False

    async def test_create_session_transport_url_is_none(self, api_client):
        resp = await api_client.post("/session/create", json={})
        body = resp.json()
        assert body.get("transport_url") is None

    async def test_create_session_with_null_user_id(self, api_client):
        resp = await api_client.post("/session/create", json={"user_id": None})
        assert resp.status_code == 200

    async def test_two_sessions_have_different_ids(self, api_client):
        r1 = await api_client.post("/session/create", json={})
        r2 = await api_client.post("/session/create", json={})
        assert r1.json()["session_id"] != r2.json()["session_id"]


class TestEndSession:
    async def test_end_existing_session_returns_200(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        end_resp = await api_client.post(f"/session/{session_id}/end")
        assert end_resp.status_code == 200

    async def test_end_existing_session_returns_ended_status(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        end_resp = await api_client.post(f"/session/{session_id}/end")
        body = end_resp.json()
        assert body["status"] == "ended"
        assert body["session_id"] == session_id

    async def test_end_nonexistent_session_returns_404(self, api_client):
        resp = await api_client.post("/session/does-not-exist/end")
        assert resp.status_code == 404
