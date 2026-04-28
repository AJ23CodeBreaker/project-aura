"""
LLM Adapter Factory

Priority:
  1. VLLM_BASE_URL set -> VLLMDialogueAdapter
  2. ANTHROPIC_API_KEY set -> AnthropicDialogueAdapter
  3. Otherwise -> StubDialogueAdapter

Never raises ImportError to callers. Falls back safely.
"""

import os

from app.adapters.llm import StubDialogueAdapter


def _is_set(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def get_llm_adapter():
    """
    Return the best available dialogue adapter for the current environment.

    Demo lane preference:
      VLLM_BASE_URL -> vLLM
    Standard fallback:
      ANTHROPIC_API_KEY -> Anthropic
    Final fallback:
      StubDialogueAdapter
    """
    if _is_set("VLLM_BASE_URL"):
        try:
            from app.adapters.vllm_llm import VLLMDialogueAdapter
            return VLLMDialogueAdapter()
        except Exception as exc:
            print(f"VLLM adapter unavailable, falling back: {exc}")

    if _is_set("ANTHROPIC_API_KEY"):
        try:
            from app.adapters.anthropic_llm import AnthropicDialogueAdapter
            return AnthropicDialogueAdapter()
        except Exception as exc:
            print(f"Anthropic adapter unavailable, falling back: {exc}")

    return StubDialogueAdapter()


def get_demo_llm_adapter():
    """
    Demo sessions should use the same priority order as the standard path,
    with vLLM preferred when configured.
    """
    return get_llm_adapter()