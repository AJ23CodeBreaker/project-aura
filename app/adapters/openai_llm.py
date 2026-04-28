"""
OpenAI-Compatible Dialogue Adapter (Phase 12A)

Targets the vLLM OpenAI-compatible API served by modal_vllm.py.
Drop-in replacement for AnthropicDialogueAdapter in the demo lane.

Configuration (via environment / settings):
  VLLM_BASE_URL   — e.g. https://your-org--aura-vllm-serve.modal.run/v1
  VLLM_API_KEY    — bearer token; vLLM does not enforce auth by default,
                    set "no-key-required" or any string if auth is off.
  VLLM_MODEL      — model name as registered in the vLLM server.
  VLLM_MAX_TOKENS — token cap per turn (default 300).

The adapter converts the internal history format
  {"role": "user"|"assistant", "text": str}
to OpenAI chat format
  {"role": "user"|"assistant", "content": str}
and injects the system prompt as the first message.

ARCHITECTURE RULE: This adapter must not be used on the standard (non-demo)
session path. It is injected exclusively via get_demo_llm_adapter() in
factory.py when VLLM_BASE_URL is configured.
"""
import os
from typing import AsyncIterator, Optional


class OpenAICompatibleDialogueAdapter:
    """
    Streams companion responses from any OpenAI-compatible /v1/chat/completions
    endpoint — specifically the vLLM instance running Dolphin-Mistral-24B.

    Implements the same interface as AnthropicDialogueAdapter so it can be
    swapped in without changes to the orchestrator or pipeline.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "openai package is not installed. Run: pip install 'openai>=1.0.0'"
            ) from exc

        resolved_base_url = base_url or os.getenv("VLLM_BASE_URL")
        if not resolved_base_url:
            raise ValueError(
                "VLLM_BASE_URL is not set. "
                "Set it to the /v1 endpoint of the vLLM Modal service."
            )

        # Normalise: openai SDK expects the base_url to end without a trailing slash
        # but the /v1 suffix must be present for the chat completions path.
        resolved_base_url = resolved_base_url.rstrip("/")
        if not resolved_base_url.endswith("/v1"):
            resolved_base_url = resolved_base_url + "/v1"

        resolved_key = api_key or os.getenv("VLLM_API_KEY", "no-key-required")
        self._model = model or os.getenv(
            "VLLM_MODEL", "cognitivecomputations/Dolphin3.0-Mistral-24B"
        )
        self._max_tokens = max_tokens or int(os.getenv("VLLM_MAX_TOKENS", "300"))

        self._client = AsyncOpenAI(
            api_key=resolved_key,
            base_url=resolved_base_url,
        )

    async def generate(
        self,
        system_prompt: str,
        conversation_history: list,
        user_message: str,
    ) -> AsyncIterator[str]:
        """
        Stream a companion response from the vLLM endpoint.

        Converts internal history format ({"role": ..., "text": ...}) to
        OpenAI chat format ({"role": ..., "content": ...}).
        System prompt is injected as the first message with role "system".
        """
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["text"]})
        messages.append({"role": "user", "content": user_message})

        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=self._max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta_content = chunk.choices[0].delta.content
            if delta_content:
                yield delta_content

    async def close(self) -> None:
        await self._client.close()
