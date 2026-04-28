"""
vLLM Dialogue Adapter

Uses a vLLM OpenAI-compatible endpoint for Aura text generation.

Expected environment variables:
  VLLM_BASE_URL   e.g. https://airjacky--aura-vllm-serve.modal.run/v1
  VLLM_MODEL      e.g. cognitivecomputations/Dolphin3.0-Mistral-24B
  VLLM_MAX_TOKENS e.g. 300
  VLLM_API_KEY    optional; leave empty if your vLLM endpoint is not protected
"""

import json
import os
from typing import AsyncIterator, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):  # type: ignore
        return False


class VLLMDialogueAdapter:
    """
    Non-streaming vLLM adapter that satisfies the async generator interface
    expected by the dialogue runner.

    It calls the OpenAI-compatible chat completions endpoint and yields the
    full assistant reply as a single chunk.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> None:
        load_dotenv()

        try:
            import httpx as _httpx
        except ImportError as exc:
            raise ImportError(
                "httpx is not installed. Add it to requirements if missing."
            ) from exc

        self._httpx = _httpx

        resolved_base = (base_url or os.getenv("VLLM_BASE_URL", "")).strip()
        if not resolved_base:
            raise ValueError("VLLM_BASE_URL is not set.")

        resolved_base = resolved_base.rstrip("/")
        if not resolved_base.endswith("/v1"):
            resolved_base = f"{resolved_base}/v1"

        self._base_url = resolved_base
        self._model = (
            model
            or os.getenv("VLLM_MODEL")
            or os.getenv("VLLM_MODEL_NAME")
            or "cognitivecomputations/Dolphin3.0-Mistral-24B"
        )
        self._max_tokens = max_tokens or int(os.getenv("VLLM_MAX_TOKENS", "300"))
        self._temperature = temperature
        self._top_p = top_p

        resolved_api_key = (api_key or os.getenv("VLLM_API_KEY", "")).strip()

        headers = {}
        if resolved_api_key and not resolved_api_key.startswith("your-"):
            headers["Authorization"] = f"Bearer {resolved_api_key}"

        self._client = _httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=120.0,
        )

    @staticmethod
    def _history_to_messages(conversation_history: list) -> list:
        messages = []
        for msg in conversation_history:
            role = msg.get("role", "user")
            text = msg.get("text", "")
            if text:
                messages.append({"role": role, "content": text})
        return messages

    @staticmethod
    def _extract_text(payload: dict) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""

        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content", "")

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        parts.append(text)
            return "".join(parts).strip()

        # Some OpenAI-compatible servers may still return plain text under choices[0].text
        fallback_text = first.get("text")
        if isinstance(fallback_text, str):
            return fallback_text.strip()

        return str(content).strip()

    async def generate(
        self,
        system_prompt: str,
        conversation_history: list,
        user_message: str,
    ) -> AsyncIterator[str]:
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._history_to_messages(conversation_history))
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "top_p": self._top_p,
            "stream": False,
        }

        # IMPORTANT: no leading slash here, or /v1 can be dropped from base_url joining
        response = await self._client.post("chat/completions", json=payload)

        if response.status_code >= 400:
            raise RuntimeError(
                f"vLLM request failed: status={response.status_code}, body={response.text[:1000]}"
            )

        try:
            payload_json = response.json()
        except Exception as exc:
            raise RuntimeError(
                f"vLLM returned non-JSON response: {response.text[:1000]}"
            ) from exc

        text = self._extract_text(payload_json)
        if not text:
            raise RuntimeError(
                "vLLM returned no assistant text. Payload was: "
                + json.dumps(payload_json)[:1500]
            )

        yield text

    async def close(self) -> None:
        await self._client.aclose()