#!/usr/bin/env python3
"""
Pipecat AI Voice Agent with Ultravox
Simplified pipeline using Ultravox unified voice AI (STT+LLM+TTS)
"""

import asyncio
import logging
import argparse
import aiohttp
import time
import os

from app.config import (
    DAILY_API_KEY,
    SAMPLE_RATE,
    STT_MODEL,
    LLM_MODEL,
)

# Pipecat imports
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams
from pipecat.transports.daily.transport import DailyTransport, DailyParams
from pipecat.frames.frames import LLMMessagesFrame

from app.ultravox_service import create_ultravox_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_daily_room() -> dict:
    """Create a new Daily room using the Daily API"""
    if not DAILY_API_KEY:
        raise ValueError("DAILY_API_KEY not found in environment variables")
    
    daily_api_url = "https://api.daily.co/v1/rooms"
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {DAILY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        expiration_time = int(time.time()) + 3600
        
        data = {
            "properties": {
                "exp": expiration_time,
                "enable_chat": False,
                "enable_screenshare": False,
                "enable_recording": False,
            }
        }
        
        async with session.post(daily_api_url, headers=headers, json=data) as response:
            if response.status != 200:
                error_text = await response.text()
                logger.error(f"Failed to create Daily room: {error_text}")
                raise Exception(f"Daily API error: {response.status}")
            
            room = await response.json()
            return room


async def run_bot(room_url: str):
    """
    Run the voice bot with simplified Ultravox pipeline.
    
    Pipeline: Daily Input → Ultravox (STT+LLM+TTS) → Daily Output
    """
    
    # 1. Create Daily Transport
    transport = DailyTransport(
        room_url=room_url,
        token=None,
        bot_name="GCP Assistant",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_sample_rate=SAMPLE_RATE,
        ),
    )
    
    # 2. Create Ultravox Service (replaces STT + LLM + TTS)
    ultravox = create_ultravox_service()
    
    # 3. Simple 3-processor pipeline (no complex aggregators)
    pipeline = Pipeline([
        transport.input(),   # Audio from Daily
        ultravox,           # Ultravox handles STT + LLM + TTS
        transport.output(),  # Audio to Daily
    ])
    
    # 4. Create Task
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
        )
    )
    
    # 5. Event Handlers
    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info(f"✅ First participant joined: {participant['id']}")
        logger.info("Ultravox will speak first with greeting")
    
    @transport.event_handler("on_participant_joined")
    async def on_participant_joined(transport, participant):
        logger.info(f"✅ Participant joined: {participant['id']}")
    
    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info(f"Participant left: {participant['id']}")
        await task.cancel()
    
    # 6. Run the pipeline
    runner = PipelineRunner()
    await runner.run(task)


async def main():
    """Main entrypoint"""
    
    parser = argparse.ArgumentParser(description="Pipecat Voice Agent with Ultravox")
    parser.add_argument("--room-url", type=str, help="Existing Daily room URL to join")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Display startup banner
    logger.info("=" * 60)
    logger.info("Pipecat AI Voice Agent (Ultravox + Daily)")
    logger.info("=" * 60)
    logger.info("✓ Using Ultravox unified voice AI")
    logger.info("  (STT + LLM + TTS in single service)")
    logger.info("=" * 60)
    
    # Get or create Daily room
    if args.room_url:
        room_url = args.room_url
        logger.info(f"Using existing room: {room_url}")
    else:
        logger.info("Creating new Daily room...")
        try:
            room = await create_daily_room()
            room_url = room["url"]
            logger.info(f"✓ Room created: {room['name']}")
            logger.info(f"✓ Room URL: {room_url}")
        except Exception as e:
            logger.error(f"❌ Failed to create Daily room: {e}")
            return
    
    logger.info("")
    logger.info("🎙️ To join this call, open the URL in your browser:")
    logger.info(f"   {room_url}")
    logger.info("")
    logger.info("🚀 Starting bot with Ultravox...")
    logger.info("=" * 60)
    
    try:
        await run_bot(room_url)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}", exc_info=True)
    finally:
        logger.info("=" * 60)
        logger.info("Goodbye!")
        logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
