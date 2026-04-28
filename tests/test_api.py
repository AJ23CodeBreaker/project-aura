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

    async def test_create_session_transport_url_is_none_for_standard_session(self, api_client):
        # Standard (non-demo) sessions always return transport_url=None.
        resp = await api_client.post("/session/create", json={})
        body = resp.json()
        assert body.get("transport_url") is None

    async def test_create_demo_session_transport_url_is_none_without_daily_key(
        self, api_client, monkeypatch
    ):
        # Demo sessions without DAILY_API_KEY gracefully return transport_url=None.
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "secret")
        monkeypatch.setattr(s.settings, "daily_api_key", None)
        resp = await api_client.post("/session/create", json={"demo_token": "secret"})
        assert resp.status_code == 200
        assert resp.json()["adult_mode"] is True
        assert resp.json().get("transport_url") is None

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


class TestDemoSessionGating:
    """
    Phase 12: demo token gating and adapter routing.

    All tests that validate token behaviour monkeypatch settings.demo_token
    so no real DEMO_TOKEN env var is required.
    """

    # ---------------------------------------------------------------------- #
    # Session creation gating
    # ---------------------------------------------------------------------- #

    async def test_no_token_creates_standard_session(self, api_client):
        resp = await api_client.post("/session/create", json={})
        assert resp.status_code == 200
        assert resp.json()["adult_mode"] is False

    async def test_valid_token_creates_adult_session(self, api_client, monkeypatch):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "secret")
        resp = await api_client.post("/session/create", json={"demo_token": "secret"})
        assert resp.status_code == 200
        assert resp.json()["adult_mode"] is True

    async def test_invalid_token_returns_403(self, api_client, monkeypatch):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "correct")
        resp = await api_client.post("/session/create", json={"demo_token": "wrong"})
        assert resp.status_code == 403

    async def test_token_not_echoed_in_response(self, api_client, monkeypatch):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "secret")
        resp = await api_client.post("/session/create", json={"demo_token": "secret"})
        assert "secret" not in resp.text
        assert "demo_token" not in resp.text

    async def test_valid_token_sets_demo_starting_closeness(self, api_client, monkeypatch):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "secret")
        monkeypatch.setattr(s.settings, "demo_starting_closeness", 3)
        resp = await api_client.post("/session/create", json={"demo_token": "secret"})
        assert resp.status_code == 200
        assert resp.json()["adult_mode"] is True
        # Verify the session carries relationship_level=3 by checking it
        # routes to the demo adapter on a subsequent turn.
        session_id = resp.json()["session_id"]
        turn_resp = await api_client.post(
            f"/session/{session_id}/turn", json={"user_text": "hi"}
        )
        assert turn_resp.status_code == 200

    # ---------------------------------------------------------------------- #
    # Adapter selection (constraint 4)
    # ---------------------------------------------------------------------- #

    async def _make_tracking_adapters(self):
        """Return (standard_adapter, demo_adapter, calls_list) tracking stubs."""
        from app.adapters.llm import StubDialogueAdapter
        calls = []

        class _Tracking(StubDialogueAdapter):
            def __init__(self, label):
                self._label = label
            async def generate(self, system_prompt, conversation_history, user_message):
                calls.append(self._label)
                yield f"[{self._label}]"

        return _Tracking("standard"), _Tracking("demo"), calls

    async def test_demo_turn_uses_demo_adapter(self, api_client, monkeypatch):
        import app.api.session as s
        std, demo, calls = await self._make_tracking_adapters()
        monkeypatch.setattr(s, "_llm_adapter", std)
        monkeypatch.setattr(s, "_demo_llm_adapter", demo)
        monkeypatch.setattr(s.settings, "demo_token", "secret")

        create = await api_client.post("/session/create", json={"demo_token": "secret"})
        sid = create.json()["session_id"]
        await api_client.post(f"/session/{sid}/turn", json={"user_text": "hi"})

        assert calls == ["demo"]

    async def test_demo_stream_uses_demo_adapter(self, api_client, monkeypatch):
        import app.api.session as s
        std, demo, calls = await self._make_tracking_adapters()
        monkeypatch.setattr(s, "_llm_adapter", std)
        monkeypatch.setattr(s, "_demo_llm_adapter", demo)
        monkeypatch.setattr(s.settings, "demo_token", "secret")

        create = await api_client.post("/session/create", json={"demo_token": "secret"})
        sid = create.json()["session_id"]
        await api_client.post(f"/session/{sid}/turn/stream", json={"user_text": "hi"})

        assert calls == ["demo"]

    async def test_normal_turn_uses_standard_adapter(self, api_client, monkeypatch):
        import app.api.session as s
        std, demo, calls = await self._make_tracking_adapters()
        monkeypatch.setattr(s, "_llm_adapter", std)
        monkeypatch.setattr(s, "_demo_llm_adapter", demo)

        create = await api_client.post("/session/create", json={})
        sid = create.json()["session_id"]
        await api_client.post(f"/session/{sid}/turn", json={"user_text": "hi"})

        assert calls == ["standard"]

    async def test_normal_stream_uses_standard_adapter(self, api_client, monkeypatch):
        import app.api.session as s
        std, demo, calls = await self._make_tracking_adapters()
        monkeypatch.setattr(s, "_llm_adapter", std)
        monkeypatch.setattr(s, "_demo_llm_adapter", demo)

        create = await api_client.post("/session/create", json={})
        sid = create.json()["session_id"]
        await api_client.post(f"/session/{sid}/turn/stream", json={"user_text": "hi"})

        assert calls == ["standard"]
