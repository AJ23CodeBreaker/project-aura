import asyncio
import os
import time

import modal

app = modal.App("daily-pipecat-smoke")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "pipecat-ai==0.0.108",
        "daily-python==0.19.9",
        "httpx>=0.25.0",
    )
)

# Keep this completely separate from Aura runtime.
# We only need DAILY_API_KEY for this smoke test.
secrets = [modal.Secret.from_name("aura-secrets")]


@app.function(
    image=image,
    secrets=secrets,
    timeout=120,
)
async def create_room_and_bot_token():
    import httpx

    daily_api_key = os.environ["DAILY_API_KEY"]
    room_name = f"daily-smoke-{int(time.time())}"

    headers = {
        "Authorization": f"Bearer {daily_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        room_resp = await client.post(
            "https://api.daily.co/v1/rooms",
            headers=headers,
            json={
                "name": room_name,
                "privacy": "public",
                "properties": {
                    "start_video_off": True,
                    "start_audio_off": False,
                    "enable_chat": False,
                    "enable_screenshare": False,
                },
            },
        )
        room_resp.raise_for_status()
        room = room_resp.json()

        token_resp = await client.post(
            "https://api.daily.co/v1/meeting-tokens",
            headers=headers,
            json={
                "properties": {
                    "room_name": room_name,
                    "is_owner": True,
                    "user_name": "Aura Smoke Bot",
                    "exp": int(time.time()) + 15 * 60,
                    "start_video_off": True,
                    "start_audio_off": False,
                }
            },
        )
        token_resp.raise_for_status()
        token = token_resp.json()["token"]

    return {
        "room_name": room_name,
        "room_url": room["url"],
        "bot_token": token,
    }


@app.function(
    image=image,
    secrets=secrets,
    timeout=180,
)
async def bot_join_smoke(room_url: str, bot_token: str):
    from pipecat.audio.vad.silero import SileroVADAnalyzer
    from pipecat.audio.vad.vad_analyzer import VADParams
    from pipecat.frames.frames import EndFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.processors.frame_processor import FrameProcessor
    from pipecat.transports.daily.transport import DailyParams, DailyTransport

    class Passthrough(FrameProcessor):
        async def process_frame(self, frame, direction):
            await super().process_frame(frame, direction)
            await self.push_frame(frame)

    transport = DailyTransport(
        room_url,
        bot_token,
        "Aura Smoke Bot",
        DailyParams(
            api_key=os.environ["DAILY_API_KEY"],
            audio_in_enabled=True,
            audio_out_enabled=True,
            transcription_enabled=False,
            vad_analyzer=SileroVADAnalyzer(
                params=VADParams(stop_secs=0.6)
            ),
        ),
    )

    @transport.event_handler("on_joined")
    async def on_joined(transport, data):
        print(f"SMOKE_JOINED: {data}")

    @transport.event_handler("on_connected")
    async def on_connected(transport, data):
        print(f"SMOKE_CONNECTED: {data}")

    @transport.event_handler("on_call_state_updated")
    async def on_call_state_updated(transport, state):
        print(f"SMOKE_CALL_STATE: {state}")

    @transport.event_handler("on_participant_joined")
    async def on_participant_joined(transport, participant):
        print(f"SMOKE_PARTICIPANT_JOINED: {participant}")

    @transport.event_handler("on_error")
    async def on_error(transport, error):
        print(f"SMOKE_ERROR: {error}")

    pipeline = Pipeline(
        [
            transport.input(),
            Passthrough(),
            transport.output(),
        ]
    )
    task = PipelineTask(pipeline)
    runner = PipelineRunner()

    async def stop_later():
        await asyncio.sleep(60)
        await task.queue_frames([EndFrame()])

    await asyncio.gather(
        runner.run(task),
        stop_later(),
    )


@app.local_entrypoint()
def main():
    info = create_room_and_bot_token.remote()
    print("")
    print("ROOM URL:")
    print(info["room_url"])
    print("")
    print("Running isolated Daily/Pipecat bot join smoke test for 60 seconds...")
    print("Open the room URL above in your browser while this runs.")
    print("Success signal: SMOKE_JOINED / SMOKE_CONNECTED in logs.")
    print("Failure signal: same native daily-emitter crash as Aura.")
    print("")

    bot_join_smoke.remote(info["room_url"], info["bot_token"])