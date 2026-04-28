"""
Transport interface, LocalTransport stub, and LiveKitTransport.

LocalTransport is the silent stub used for local pipeline smoke-testing.

LiveKitTransport wraps pipecat-ai's LiveKit integration and provides server-side
WebRTC audio I/O via LiveKit rooms.

Important:
- This file adds the new LiveKit transport path.
- Do not deploy immediately after only this file change.
- The API/session bootstrap path still needs to be migrated in the next step.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from app.config.settings import settings


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
    """

    async def audio_input_stream(self) -> AsyncIterator[bytes]:
        yield b"\x00" * 160

    async def send_audio(self, audio_bytes: bytes) -> None:
        pass


class LiveKitTransport(TransportBase):
    """
    LiveKit WebRTC transport via pipecat-ai's LiveKitTransport.

    The server-side bot joins a LiveKit room as an audio participant.
    Audio frames from the user flow in through input(); generated audio
    flows out through output().

    Required:
      - LIVEKIT_URL in settings or passed explicitly
      - token
      - room_name
    """

    def __init__(
        self,
        room_name: str,
        token: str,
        livekit_url: Optional[str] = None,
    ) -> None:
        self._room_name = room_name
        self._token = token
        self._livekit_url = livekit_url or settings.livekit_url
        self._transport = None

        if not self._livekit_url:
            raise ValueError("LIVEKIT_URL is not configured.")

        if not self._token:
            raise ValueError("LiveKit token is required.")

        if not self._room_name:
            raise ValueError("LiveKit room_name is required.")

    def _init(self):
        """Lazy-initialise the pipecat LiveKitTransport instance."""
        if self._transport is not None:
            return

        try:
            from pipecat.transports.livekit.transport import (
                LiveKitParams,
                LiveKitTransport as _PipecatLiveKitTransport,
            )
        except ImportError as exc:
            raise ImportError(
                "Pipecat LiveKit transport is not available. "
                "Ensure pipecat-ai[livekit] is installed."
            ) from exc

        params = LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        )

        self._transport = _PipecatLiveKitTransport(
            url=self._livekit_url,
            token=self._token,
            room_name=self._room_name,
            params=params,
        )

    def input(self):
        """
        Pipecat FrameProcessor for inbound LiveKit room media/events.
        """
        self._init()
        return self._transport.input()

    def output(self):
        """
        Pipecat FrameProcessor for outbound generated audio.
        """
        self._init()
        return self._transport.output()

    def get_pipecat_transport(self):
        """Return the underlying pipecat LiveKitTransport."""
        self._init()
        return self._transport

    def event_handler(self, event_name: str):
        """
        Pass-through decorator for Pipecat transport event handlers.
        """
        self._init()
        return self._transport.event_handler(event_name)

    async def audio_input_stream(self) -> AsyncIterator[bytes]:
        """
        Not used in the live LiveKit pipeline; input()/output() drive frame flow.
        """
        yield b"\x00" * 160

    async def send_audio(self, audio_bytes: bytes) -> None:
        """
        Not used in the live LiveKit pipeline; output goes through output().
        """
        pass