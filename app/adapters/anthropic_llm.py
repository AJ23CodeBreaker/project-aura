"""
Anthropic Dialogue Adapter (optional)

Concrete implementation of DialogueAdapter using the Anthropic API.

USAGE:
  Only activate when ANTHROPIC_API_KEY is set in the environment.
  StubDialogueAdapter remains the default throughout the codebase.
  This adapter is never used automatically — it must be passed explicitly
  to build_pipeline() or the runner test functions.

INSTALLATION:
  pip install anthropic

EXAMPLE:
  import os
  from app.adapters.anthropic_llm import AnthropicDialogueAdapter
  from app.orchestrator.pipeline import build_pipeline

  adapter = AnthropicDialogueAdapter()   # reads ANTHROPIC_API_KEY from env
  pipeline = build_pipeline(llm_adapter=adapter)

REQUIREMENTS:
  - ANTHROPIC_API_KEY must be set in .env or environment.
  - anthropic Python package must be installed.
  - Does not change any pipeline, orchestrator, or context code.
"""
import os
from typing import AsyncIterator, Optional


class AnthropicDialogueAdapter:
    """
    Streams companion responses from Anthropic's Claude API.

    Implements the same interface as DialogueAdapter so it can be dropped
    into build_pipeline() or any test runner without other code changes.

    Defaults:
      model  — claude-sonnet-4-6 (fast, suitable for voice latency)
      max_tokens — 200 (short spoken turns; override via LLM_MAX_TOKENS env)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> None:
        try:
            import anthropic as _anthropic
        except ImportError as exc:
            raise ImportError(
                "anthropic package is not installed. "
                "Run: pip install anthropic"
            ) from exc

        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to .env or pass api_key= directly."
            )

        self._model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-6")
        self._max_tokens = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "200"))
        self._client = _anthropic.AsyncAnthropic(api_key=key)

    async def generate(
        self,
        system_prompt: str,
        conversation_history: list,
        user_message: str,
    ) -> AsyncIterator[str]:
        """
        Stream a companion response from the Anthropic API.

        Converts the internal history format ({"role": ..., "text": ...})
        to the Anthropic format ({"role": ..., "content": ...}).
        """
        messages = [
            {"role": msg["role"], "content": msg["text"]}
            for msg in conversation_history
        ]
        messages.append({"role": "user", "content": user_message})

        async with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def close(self) -> None:
        await self._client.close()
