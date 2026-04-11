"""
Transport interface and LocalTransport stub

The live transport target is DailyTransport (Daily.co WebRTC via pipecat).
That requires a Daily.co API key and is not wired in Phase 3.

LocalTransport is an extremely lightweight stub for local pipeline testing only.
It yields one silent audio frame and discards all output.
Its only purpose is to let run_fake_turn() prove the pipeline can be
instantiated and a fake turn can pass through without a real audio device
or network connection.

Do not add complexity to LocalTransport. If more test fidelity is needed,
wire DailyTransport instead.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator


class TransportBase(ABC):
    """Minimal interface any transport must satisfy."""

    @abstractmethod
    async def audio_input_stream(self) -> AsyncIterator[bytes]:
        """Yield raw PCM audio bytes from the user."""
        ...

    @abstractmethod
    async def send_audio(self, audio_bytes: bytes) -> None:
        """Deliver companion audio bytes to the client."""
        ...


class LocalTransport(TransportBase):
    """
    Minimal local stub for pipeline testing.

    Yields one 160-byte silent PCM frame (10 ms at 16 kHz mono),
    then stops. Discards all output audio.

    Not suitable for production. Replace with DailyTransport for live use.
    """

    async def audio_input_stream(self) -> AsyncIterator[bytes]:
        yield b"\x00" * 160  # one silent PCM frame — enough to trigger the pipeline

    async def send_audio(self, audio_bytes: bytes) -> None:
        pass  # discard — LocalTransport does not deliver audio to a real client
