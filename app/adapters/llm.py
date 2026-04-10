"""
LLM Dialogue Adapter Interface — STUB

Defines the contract for the companion's conversational brain.
The live provider is not yet selected or integrated.

Assumptions:
- Must produce spoken-style responses, not essay-style chatbot output.
- System prompt injects: persona, memory context, relationship state,
  and intimacy policy.
- Streaming output is required to reduce first-audio latency.
- Provider secrets must never appear in frontend code.

Next step (Phase 3): implement a concrete adapter (e.g. AnthropicDialogueAdapter)
that satisfies this interface and wire it into the Pipecat orchestrator.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class DialogueAdapter(ABC):

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        conversation_history: list,
        user_message: str,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming companion response.

        Args:
            system_prompt:         Composed persona + memory + relationship-state
                                   instructions. Built by the orchestrator each turn.
            conversation_history:  Recent turns as a short rolling window.
                                   Not a full raw transcript.
            user_message:          Current user utterance from STT.

        Yields:
            Text chunks as they stream from the model.
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        ...


class StubDialogueAdapter(DialogueAdapter):
    """
    STUB — returns a canned spoken-style response for local testing only.
    Replace with a real provider adapter before any voice testing.
    """

    async def generate(
        self,
        system_prompt: str,
        conversation_history: list,
        user_message: str,
    ) -> AsyncIterator[str]:
        response = "Hey, I heard you. I'm not fully wired up yet, but I'm here."
        for word in response.split():
            yield word + " "

    async def close(self) -> None:
        pass
