import asyncio
import datetime
import os
import secrets

import modal

app = modal.App("livekit-smoke")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "pipecat-ai[livekit]==0.0.108",
        "livekit-api",
        "python-dotenv",
    )
)

secrets_cfg = [modal.Secret.from_name("livekit-smoke-secrets")]


@app.function(
    image=image,
    secrets=secrets_cfg,
    timeout=60,
)
def make_tokens():
    from livekit.api import AccessToken, VideoGrants

    room_name = f"aura-smoke-{secrets.token_hex(4)}"

    user_token = (
        AccessToken()
        .with_identity(f"user-{secrets.token_hex(3)}")
        .with_name("Smoke User")
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
            )
        )
        .with_ttl(datetime.timedelta(hours=1))
        .to_jwt()
    )

    bot_token = (
        AccessToken()
        .with_identity(f"bot-{secrets.token_hex(3)}")
        .with_name("Aura Smoke Bot")
        .with_kind("agent")
        .with_grants(
            VideoGrants(
                room_join=True,
                room=room_name,
            )
        )
        .with_ttl(datetime.timedelta(hours=1))
        .to_jwt()
    )

    return {
        "room_name": room_name,
        "livekit_url": os.environ["LIVEKIT_URL"],
        "user_token": user_token,
        "bot_token": bot_token,
    }


@app.function(
    image=image,
    secrets=secrets_cfg,
    timeout=180,
)
async def bot_join_smoke(livekit_url: str, room_name: str, bot_token: str):
    from pipecat.frames.frames import EndFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.processors.frame_processor import FrameProcessor
    from pipecat.transports.livekit.transport import LiveKitParams, LiveKitTransport

    class Passthrough(FrameProcessor):
        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            await self.push_frame(frame)

    transport = LiveKitTransport(
        url=livekit_url,
        token=bot_token,
        room_name=room_name,
        params=LiveKitParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    )

    @transport.event_handler("on_connected")
    async def on_connected(transport):
        print("LK_CONNECTED")

    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        print(f"LK_CALL_STATE: {state}")

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant_id):
        print(f"LK_FIRST_PARTICIPANT_JOINED: {participant_id}")

    @transport.event_handler("on_participant_connected")
    async def on_participant_connected(transport, participant_id):
        print(f"LK_PARTICIPANT_CONNECTED: {participant_id}")

    @transport.event_handler("on_participant_disconnected")
    async def on_participant_disconnected(transport, participant_id):
        print(f"LK_PARTICIPANT_DISCONNECTED: {participant_id}")

    @transport.event_handler("on_disconnected")
    async def on_disconnected(transport):
        print("LK_DISCONNECTED")

    pipeline = Pipeline(
        [
            transport.input(),
            Passthrough(),
            transport.output(),
        ]
    )

    task = PipelineTask(pipeline)
    runner = PipelineRunner(handle_sigint=False)

    async def stop_later():
        await asyncio.sleep(90)
        await task.queue_frames([EndFrame()])

    await asyncio.gather(
        runner.run(task),
        stop_later(),
    )


@app.local_entrypoint()
def main():
    info = make_tokens.remote()

    print("")
    print("LIVEKIT URL:")
    print(info["livekit_url"])
    print("")
    print("ROOM NAME:")
    print(info["room_name"])
    print("")
    print("USER TOKEN:")
    print(info["user_token"])
    print("")
    print("NEXT:")
    print("1. Open https://meet.livekit.io")
    print("2. Open the Custom tab")
    print("3. Paste LIVEKIT URL")
    print("4. Paste USER TOKEN")
    print("5. Join the room")
    print("")
    print("SUCCESS SIGNALS IN LOGS:")
    print("LK_CONNECTED")
    print("LK_FIRST_PARTICIPANT_JOINED")
    print("")

    bot_join_smoke.remote(
        info["livekit_url"],
        info["room_name"],
        info["bot_token"],
    )