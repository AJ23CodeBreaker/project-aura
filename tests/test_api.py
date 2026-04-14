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


class TestTurnEndpoint:
    async def test_turn_returns_200(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn",
            json={"user_text": "Hello, are you there?"},
        )
        assert resp.status_code == 200

    async def test_turn_returns_assistant_text(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn",
            json={"user_text": "Hello"},
        )
        body = resp.json()
        assert "assistant_text" in body
        assert len(body["assistant_text"]) > 0

    async def test_turn_returns_session_id(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn",
            json={"user_text": "Hello"},
        )
        assert resp.json()["session_id"] == session_id

    async def test_turn_nonexistent_session_returns_404(self, api_client):
        resp = await api_client.post(
            "/session/does-not-exist/turn",
            json={"user_text": "Hello"},
        )
        assert resp.status_code == 404

    async def test_turn_on_ended_session_returns_404(self, api_client):
        # Regression test: ended sessions must not accept further turns.
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]

        # End the session
        await api_client.post(f"/session/{session_id}/end")

        # Subsequent turn must be rejected
        resp = await api_client.post(
            f"/session/{session_id}/turn",
            json={"user_text": "Hello after end"},
        )
        assert resp.status_code == 404

    async def test_multiple_turns_same_session(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]

        for msg in ["Hello", "How are you?", "Tell me something"]:
            resp = await api_client.post(
                f"/session/{session_id}/turn",
                json={"user_text": msg},
            )
            assert resp.status_code == 200
            assert len(resp.json()["assistant_text"]) > 0


class TestTurnStreamEndpoint:
    async def test_stream_returns_200(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn/stream",
            json={"user_text": "Hello"},
        )
        assert resp.status_code == 200

    async def test_stream_content_type_is_event_stream(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn/stream",
            json={"user_text": "Hello"},
        )
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_stream_contains_data_lines(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn/stream",
            json={"user_text": "Hello"},
        )
        data_lines = [
            l for l in resp.text.split("\n") if l.startswith("data: ")
        ]
        assert len(data_lines) > 0

    async def test_stream_ends_with_done(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn/stream",
            json={"user_text": "Hello"},
        )
        assert "data: [DONE]" in resp.text

    async def test_stream_assembled_text_is_nonempty(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        resp = await api_client.post(
            f"/session/{session_id}/turn/stream",
            json={"user_text": "Hello"},
        )
        tokens = [
            l[6:] for l in resp.text.split("\n")
            if l.startswith("data: ") and l != "data: [DONE]"
        ]
        assert len("".join(tokens)) > 0

    async def test_stream_nonexistent_session_returns_404(self, api_client):
        resp = await api_client.post(
            "/session/does-not-exist/turn/stream",
            json={"user_text": "Hello"},
        )
        assert resp.status_code == 404

    async def test_stream_ended_session_returns_404(self, api_client):
        create_resp = await api_client.post("/session/create", json={})
        session_id = create_resp.json()["session_id"]
        await api_client.post(f"/session/{session_id}/end")
        resp = await api_client.post(
            f"/session/{session_id}/turn/stream",
            json={"user_text": "Hello"},
        )
        assert resp.status_code == 404
