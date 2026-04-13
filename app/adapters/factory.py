"""
LLM Adapter Factory

Returns the appropriate DialogueAdapter based on environment configuration.

Priority:
  1. ANTHROPIC_API_KEY is set and anthropic package is installed
     → AnthropicDialogueAdapter (real Claude responses)
  2. Otherwise → StubDialogueAdapter (canned response, no credentials needed)

Importing this module never raises — the anthropic package import is deferred
inside AnthropicDialogueAdapter.__init__, so a missing package only falls back
to the stub rather than crashing at import time.
"""
import os

from app.adapters.llm import DialogueAdapter, StubDialogueAdapter


def get_llm_adapter() -> DialogueAdapter:
    """
    Return the appropriate LLM adapter based on environment configuration.

    Falls back to StubDialogueAdapter if ANTHROPIC_API_KEY is not set or if
    the anthropic package is not installed. Never raises ImportError.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from app.adapters.anthropic_llm import AnthropicDialogueAdapter
            return AnthropicDialogueAdapter()
        except ImportError:
            # anthropic package not installed — fall through to stub
            pass
    return StubDialogueAdapter()
