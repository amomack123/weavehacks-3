import os
from pipecat.runner.types import RunnerArguments
import aiohttp
from pipecat.runner.daily import configure
from fastapi import FastAPIs



async with aiohttp.ClientSession() as session:
    # Returns a DailyRoomConfig object
    room_config = await configure(session)

    room_url = room_config.room_url
    token = room_config.token

    # Use with DailyTransport
    transport = DailyTransport(room_url, token, "Bot Name", params=DailyParams())

async def bot(runner_args: RunnerArguments):
    """Main bot entry point called by the development runner."""

    # Create your transport based on the runner arguments
    transport = SmallWebRTCTransport(
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
        webrtc_connection=runner_args.webrtc_connection,
    )

    # Run your bot logic
    await run_bot(transport)

app = FastAPI()
@app.post("/uploadframe")
async def upload_frame():
    # Your logic to collect the PNG goes here
    return {"status": "frame collected"}




if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
