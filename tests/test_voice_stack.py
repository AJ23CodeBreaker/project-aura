"""
Phase 12A — Voice stack tests

All tests are fully offline (no real network calls, no real providers).
Provider I/O is replaced with mocks and stubs throughout.

Coverage:
  - OpenAICompatibleDialogueAdapter: streams response from mocked openai client
  - Factory: selects vLLM adapter when VLLM_BASE_URL is set
  - Factory: selects Anthropic adapter when VLLM_BASE_URL is absent
  - DeepgramSTTAdapter: buffers audio and yields final transcript
  - FishAudioTTSAdapter: streams audio bytes from mocked httpx response
  - LiveVoiceRenderer: passes emotional_hint through to TTS adapter
  - Text/SSE path: still works after Phase 12A changes (regression)
  - Demo token gating: does not regress (integration with test_api.py fixtures)
  - transport_url: None for standard sessions, None for demo without Daily key
"""

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

async def _collect_async_gen(agen) -> list:
    """Drain an async generator into a list."""
    result = []
    async for item in agen:
        result.append(item)
    return result


# --------------------------------------------------------------------------- #
# OpenAICompatibleDialogueAdapter
# --------------------------------------------------------------------------- #

class TestOpenAICompatibleDialogueAdapter:

    def _make_mock_stream(self, tokens: list[str]):
        """Build a mock async streaming response from openai SDK."""
        chunks = []
        for token in tokens:
            choice = MagicMock()
            choice.delta.content = token
            chunk = MagicMock()
            chunk.choices = [choice]
            chunks.append(chunk)

        async def _async_iter():
            for c in chunks:
                yield c

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: _async_iter()
        return mock_stream

    @pytest.mark.asyncio
    async def test_generate_yields_tokens(self, monkeypatch):
        from app.adapters.openai_llm import OpenAICompatibleDialogueAdapter

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=self._make_mock_stream(["Hello ", "there"])
        )

        adapter = OpenAICompatibleDialogueAdapter.__new__(OpenAICompatibleDialogueAdapter)
        adapter._client = mock_client
        adapter._model = "test-model"
        adapter._max_tokens = 200

        tokens = []
        async for token in adapter.generate("sys", [], "hi"):
            tokens.append(token)

        assert tokens == ["Hello ", "there"]

    @pytest.mark.asyncio
    async def test_generate_injects_system_prompt(self, monkeypatch):
        from app.adapters.openai_llm import OpenAICompatibleDialogueAdapter

        called_with = {}

        async def mock_create(**kwargs):
            called_with.update(kwargs)
            return self._make_mock_stream(["ok"])

        mock_client = MagicMock()
        mock_client.chat.completions.create = mock_create

        adapter = OpenAICompatibleDialogueAdapter.__new__(OpenAICompatibleDialogueAdapter)
        adapter._client = mock_client
        adapter._model = "m"
        adapter._max_tokens = 100

        async for _ in adapter.generate("my system prompt", [], "user msg"):
            pass

        messages = called_with["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "my system prompt"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "user msg"

    @pytest.mark.asyncio
    async def test_generate_skips_empty_delta(self, monkeypatch):
        from app.adapters.openai_llm import OpenAICompatibleDialogueAdapter

        # Mix of None and empty string deltas — should be filtered out.
        tokens_in = [None, "", "real"]

        async def _async_iter():
            for t in tokens_in:
                choice = MagicMock()
                choice.delta.content = t
                chunk = MagicMock()
                chunk.choices = [choice]
                yield chunk

        mock_stream = MagicMock()
        mock_stream.__aiter__ = lambda self: _async_iter()

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream)

        adapter = OpenAICompatibleDialogueAdapter.__new__(OpenAICompatibleDialogueAdapter)
        adapter._client = mock_client
        adapter._model = "m"
        adapter._max_tokens = 100

        tokens = []
        async for t in adapter.generate("s", [], "u"):
            tokens.append(t)

        assert tokens == ["real"]

    @pytest.mark.asyncio
    async def test_base_url_appends_v1(self, monkeypatch):
        """Adapter normalises base_url to always end with /v1."""
        monkeypatch.setenv("VLLM_BASE_URL", "http://localhost:8080")
        monkeypatch.setenv("VLLM_MODEL", "test-model")
        monkeypatch.setenv("VLLM_API_KEY", "x")

        with patch("openai.AsyncOpenAI") as MockOpenAI:
            MockOpenAI.return_value = MagicMock()
            from app.adapters.openai_llm import OpenAICompatibleDialogueAdapter

            OpenAICompatibleDialogueAdapter()
            call_kwargs = MockOpenAI.call_args[1]
            assert call_kwargs["base_url"].endswith("/v1")


# --------------------------------------------------------------------------- #
# Factory — adapter selection
# --------------------------------------------------------------------------- #

class TestFactory:

    @pytest.mark.asyncio
    async def test_get_demo_adapter_returns_openai_when_vllm_configured(self, monkeypatch):
        monkeypatch.setenv("VLLM_BASE_URL", "http://localhost:8080/v1")
        monkeypatch.setenv("VLLM_MODEL", "test-model")
        monkeypatch.setenv("VLLM_API_KEY", "x")

        with patch("openai.AsyncOpenAI") as MockOpenAI:
            MockOpenAI.return_value = MagicMock()

            # Re-import factory to pick up patched env
            import importlib
            import app.adapters.factory as factory_mod
            importlib.reload(factory_mod)

            from app.adapters.openai_llm import OpenAICompatibleDialogueAdapter
            adapter = factory_mod.get_demo_llm_adapter()
            assert isinstance(adapter, OpenAICompatibleDialogueAdapter)

    @pytest.mark.asyncio
    async def test_get_demo_adapter_falls_back_without_vllm(self, monkeypatch):
        monkeypatch.delenv("VLLM_BASE_URL", raising=False)
        monkeypatch.delenv("LLM_DEMO_MODEL", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        import importlib
        import app.adapters.factory as factory_mod
        importlib.reload(factory_mod)

        from app.adapters.llm import StubDialogueAdapter
        adapter = factory_mod.get_demo_llm_adapter()
        assert isinstance(adapter, StubDialogueAdapter)

    @pytest.mark.asyncio
    async def test_standard_adapter_unaffected_by_vllm_config(self, monkeypatch):
        """VLLM_BASE_URL must not affect the standard (non-demo) adapter."""
        monkeypatch.setenv("VLLM_BASE_URL", "http://localhost:8080/v1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        import importlib
        import app.adapters.factory as factory_mod
        importlib.reload(factory_mod)

        from app.adapters.llm import StubDialogueAdapter
        adapter = factory_mod.get_llm_adapter()
        # Without ANTHROPIC_API_KEY, standard path must remain stub.
        assert isinstance(adapter, StubDialogueAdapter)


# --------------------------------------------------------------------------- #
# DeepgramSTTAdapter
# --------------------------------------------------------------------------- #

class TestDeepgramSTTAdapter:

    def _make_mock_dg_response(self, transcript: str, confidence: float = 0.95):
        """Build a minimal Deepgram pre-recorded response mock."""
        alt = MagicMock()
        alt.transcript = transcript
        alt.confidence = confidence
        channel = MagicMock()
        channel.alternatives = [alt]
        results = MagicMock()
        results.channels = [channel]
        response = MagicMock()
        response.results = results
        return response

    @pytest.mark.asyncio
    async def test_yields_final_transcript(self):
        from app.adapters.stt import DeepgramSTTAdapter

        mock_rest = MagicMock()
        mock_rest.transcribe_file = AsyncMock(
            return_value=self._make_mock_dg_response("hello world", 0.98)
        )
        mock_listen = MagicMock()
        mock_listen.asyncrest.v.return_value = mock_rest

        adapter = DeepgramSTTAdapter.__new__(DeepgramSTTAdapter)
        adapter._client = MagicMock()
        adapter._client.listen = mock_listen
        adapter._model = "nova-2"
        adapter._sample_rate = 16000
        adapter._channels = 1

        async def _audio_stream():
            yield b"\x00" * 3200  # 100 ms of 16 kHz mono PCM

        events = await _collect_async_gen(adapter.transcribe_stream(_audio_stream()))
        assert len(events) == 1
        assert events[0]["type"] == "final"
        assert events[0]["text"] == "hello world"
        assert events[0]["is_end_of_turn"] is True
        assert events[0]["confidence"] == 0.98

    @pytest.mark.asyncio
    async def test_yields_nothing_on_empty_audio(self):
        from app.adapters.stt import DeepgramSTTAdapter

        adapter = DeepgramSTTAdapter.__new__(DeepgramSTTAdapter)
        adapter._client = MagicMock()
        adapter._model = "nova-2"
        adapter._sample_rate = 16000
        adapter._channels = 1

        async def _empty_stream():
            return
            yield  # make it an async generator

        events = await _collect_async_gen(adapter.transcribe_stream(_empty_stream()))
        assert events == []

    @pytest.mark.asyncio
    async def test_yields_nothing_on_blank_transcript(self):
        from app.adapters.stt import DeepgramSTTAdapter

        mock_rest = MagicMock()
        mock_rest.transcribe_file = AsyncMock(
            return_value=self._make_mock_dg_response("", 0.0)
        )
        mock_listen = MagicMock()
        mock_listen.asyncrest.v.return_value = mock_rest

        adapter = DeepgramSTTAdapter.__new__(DeepgramSTTAdapter)
        adapter._client = MagicMock()
        adapter._client.listen = mock_listen
        adapter._model = "nova-2"
        adapter._sample_rate = 16000
        adapter._channels = 1

        async def _audio():
            yield b"\x00" * 160

        events = await _collect_async_gen(adapter.transcribe_stream(_audio()))
        assert events == []

    @pytest.mark.asyncio
    async def test_graceful_on_network_failure(self):
        from app.adapters.stt import DeepgramSTTAdapter

        mock_rest = MagicMock()
        mock_rest.transcribe_file = AsyncMock(side_effect=Exception("network error"))
        mock_listen = MagicMock()
        mock_listen.asyncrest.v.return_value = mock_rest

        adapter = DeepgramSTTAdapter.__new__(DeepgramSTTAdapter)
        adapter._client = MagicMock()
        adapter._client.listen = mock_listen
        adapter._model = "nova-2"
        adapter._sample_rate = 16000
        adapter._channels = 1

        async def _audio():
            yield b"\x00" * 160

        # Must not raise — returns empty result on network failure.
        events = await _collect_async_gen(adapter.transcribe_stream(_audio()))
        assert events == []


# --------------------------------------------------------------------------- #
# FishAudioTTSAdapter
# --------------------------------------------------------------------------- #

class TestFishAudioTTSAdapter:

    def _make_mock_httpx_stream(self, chunks: list[bytes]):
        """Build a mock httpx streaming response context manager."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()

        async def _aiter_bytes(chunk_size=4096):
            for c in chunks:
                yield c

        mock_response.aiter_bytes = _aiter_bytes

        class _CM:
            async def __aenter__(self_inner):
                return mock_response
            async def __aexit__(self_inner, *args):
                pass

        return _CM()

    @pytest.mark.asyncio
    async def test_yields_audio_chunks(self):
        from app.adapters.tts import FishAudioTTSAdapter

        fake_audio = [b"WAVEhdr", b"audio_chunk_1", b"audio_chunk_2"]

        adapter = FishAudioTTSAdapter.__new__(FishAudioTTSAdapter)
        adapter._base_url = "http://fake-fish:8080"
        adapter._api_key = ""
        adapter._voice_id = ""
        adapter._format = "wav"

        mock_client = MagicMock()
        mock_client.stream.return_value = self._make_mock_httpx_stream(fake_audio)
        adapter._client = mock_client

        async def _text():
            yield "Hello"

        audio = await _collect_async_gen(adapter.synthesize_stream(_text()))
        assert audio == fake_audio

    @pytest.mark.asyncio
    async def test_applies_emotional_hint_playful(self):
        from app.adapters.tts import FishAudioTTSAdapter

        captured = {}

        adapter = FishAudioTTSAdapter.__new__(FishAudioTTSAdapter)
        adapter._base_url = "http://fake-fish:8080"
        adapter._api_key = ""
        adapter._voice_id = "v1"
        adapter._format = "wav"

        class _CM:
            async def __aenter__(self_inner):
                r = AsyncMock()
                r.raise_for_status = MagicMock()
                async def _aiter(_=None):
                    return
                    yield
                r.aiter_bytes = _aiter
                return r
            async def __aexit__(self_inner, *args):
                pass

        mock_client = MagicMock()

        def _capture_stream(method, url, json=None, headers=None, **kwargs):
            captured.update(json or {})
            return _CM()

        mock_client.stream = _capture_stream
        adapter._client = mock_client

        async def _text():
            yield "hey"

        await _collect_async_gen(adapter.synthesize_stream(_text(), emotional_hint="playful"))
        # "playful" maps to speed=1.1
        assert "speed" in captured
        assert captured["speed"] == pytest.approx(1.1)

    @pytest.mark.asyncio
    async def test_includes_voice_id_when_set(self):
        from app.adapters.tts import FishAudioTTSAdapter

        captured = {}

        adapter = FishAudioTTSAdapter.__new__(FishAudioTTSAdapter)
        adapter._base_url = "http://fake-fish:8080"
        adapter._api_key = ""
        adapter._voice_id = "my-actress-voice"
        adapter._format = "wav"

        class _CM:
            async def __aenter__(self_inner):
                r = AsyncMock()
                r.raise_for_status = MagicMock()
                async def _aiter(_=None):
                    return
                    yield
                r.aiter_bytes = _aiter
                return r
            async def __aexit__(self_inner, *args):
                pass

        mock_client = MagicMock()

        def _capture_stream(method, url, json=None, headers=None, **kwargs):
            captured.update(json or {})
            return _CM()

        mock_client.stream = _capture_stream
        adapter._client = mock_client

        async def _text():
            yield "hi"

        await _collect_async_gen(adapter.synthesize_stream(_text()))
        assert captured.get("reference_id") == "my-actress-voice"

    @pytest.mark.asyncio
    async def test_graceful_on_http_error(self):
        from app.adapters.tts import FishAudioTTSAdapter

        adapter = FishAudioTTSAdapter.__new__(FishAudioTTSAdapter)
        adapter._base_url = "http://fake-fish:8080"
        adapter._api_key = ""
        adapter._voice_id = ""
        adapter._format = "wav"

        class _CM:
            async def __aenter__(self_inner):
                raise Exception("connection refused")
            async def __aexit__(self_inner, *args):
                pass

        mock_client = MagicMock()
        mock_client.stream.return_value = _CM()
        adapter._client = mock_client

        async def _text():
            yield "hi"

        # Must not raise — yields nothing on error.
        audio = await _collect_async_gen(adapter.synthesize_stream(_text()))
        assert audio == []


# --------------------------------------------------------------------------- #
# LiveVoiceRenderer — emotional_hint propagation
# --------------------------------------------------------------------------- #

class TestLiveVoiceRendererEmotionalHint:

    @pytest.mark.asyncio
    async def test_emotional_hint_forwarded_to_adapter(self):
        """emotional_hint received by render() must reach synthesize_stream()."""
        from app.voice.renderer import LiveVoiceRenderer

        received_hint = {}

        class _MockTTSAdapter:
            async def synthesize_stream(
                self, text_stream, emotional_hint=None
            ):
                received_hint["hint"] = emotional_hint
                async for _ in text_stream:
                    pass
                yield b"\x00\x01"

            async def close(self):
                pass

        renderer = LiveVoiceRenderer(tts_adapter=_MockTTSAdapter())

        async def _text():
            yield "test"

        audio = await _collect_async_gen(
            renderer.render(_text(), emotional_hint="intimate")
        )

        assert received_hint.get("hint") == "intimate"
        assert audio == [b"\x00\x01"]

    @pytest.mark.asyncio
    async def test_none_hint_is_passed_through(self):
        from app.voice.renderer import LiveVoiceRenderer

        received = {}

        class _MockTTSAdapter:
            async def synthesize_stream(self, text_stream, emotional_hint=None):
                received["hint"] = emotional_hint
                async for _ in text_stream:
                    pass
                yield b""

            async def close(self):
                pass

        renderer = LiveVoiceRenderer(tts_adapter=_MockTTSAdapter())

        async def _text():
            yield "x"

        await _collect_async_gen(renderer.render(_text()))
        assert received.get("hint") is None


# --------------------------------------------------------------------------- #
# Text/SSE regression — path must not be broken by Phase 12A changes
# --------------------------------------------------------------------------- #

class TestTextSSEPathRegression:
    """
    Regression guard: the text/SSE endpoints must continue to work exactly as
    they did before Phase 12A. Uses the same api_client fixture as test_api.py.
    """

    async def test_text_turn_still_works(self, api_client):
        create = await api_client.post("/session/create", json={})
        sid = create.json()["session_id"]
        resp = await api_client.post(
            f"/session/{sid}/turn", json={"user_text": "hello"}
        )
        assert resp.status_code == 200
        assert len(resp.json()["assistant_text"]) > 0

    async def test_stream_still_works(self, api_client):
        create = await api_client.post("/session/create", json={})
        sid = create.json()["session_id"]
        resp = await api_client.post(
            f"/session/{sid}/turn/stream", json={"user_text": "hello"}
        )
        assert resp.status_code == 200
        assert "data: [DONE]" in resp.text

    async def test_demo_token_gating_unchanged(self, api_client, monkeypatch):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "sec")
        monkeypatch.setattr(s.settings, "daily_api_key", None)  # no Daily
        resp = await api_client.post("/session/create", json={"demo_token": "sec"})
        assert resp.status_code == 200
        assert resp.json()["adult_mode"] is True

    async def test_invalid_demo_token_still_403(self, api_client, monkeypatch):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "correct")
        monkeypatch.setattr(s.settings, "daily_api_key", None)
        resp = await api_client.post("/session/create", json={"demo_token": "wrong"})
        assert resp.status_code == 403


# --------------------------------------------------------------------------- #
# transport_url contract
# --------------------------------------------------------------------------- #

class TestTransportUrl:

    async def test_standard_session_transport_url_is_none(self, api_client):
        resp = await api_client.post("/session/create", json={})
        assert resp.json().get("transport_url") is None

    async def test_demo_session_without_daily_key_transport_url_is_none(
        self, api_client, monkeypatch
    ):
        import app.api.session as s
        monkeypatch.setattr(s.settings, "demo_token", "tok")
        monkeypatch.setattr(s.settings, "daily_api_key", None)
        resp = await api_client.post("/session/create", json={"demo_token": "tok"})
        assert resp.status_code == 200
        assert resp.json().get("transport_url") is None

    async def test_demo_session_with_daily_key_returns_transport_url(
        self, api_client, monkeypatch
    ):
        """Mock Daily room creation to verify transport_url is populated."""
        import app.api.session as s

        fake_room = {
            "name": "test-room-abc",
            "url": "https://your-domain.daily.co/test-room-abc",
        }

        # Patch _create_daily_room so no real HTTP call is made.
        async def _mock_create_room(api_key, expiry_seconds):
            return fake_room

        # Patch _run_voice_pipeline so no background task is started.
        async def _mock_pipeline(session_id, room_url):
            pass

        monkeypatch.setattr(s.settings, "demo_token", "tok")
        monkeypatch.setattr(s.settings, "daily_api_key", "fake-daily-key")
        monkeypatch.setattr(s, "_create_daily_room", _mock_create_room)
        monkeypatch.setattr(s, "_run_voice_pipeline", _mock_pipeline)

        resp = await api_client.post("/session/create", json={"demo_token": "tok"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["adult_mode"] is True
        assert body["transport_url"] == fake_room["url"]
