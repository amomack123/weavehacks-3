"""
Pipecat Voice Bot for GCP Assistant.

Optimized for Pipecat Playground with Daily Transport.

Features:
    - Dynamic Daily Room creation using DAILY_API_KEY
    - Screen share capture converted to Base64 for Brain API
    - Cartesia TTS for natural voice interaction
    - Modern LLMContext and AggregatorPair for UI visibility

Environment Variables:
    DAILY_API_KEY: Daily.co API key for room creation
    DAILY_SAMPLE_ROOM_URL: Optional static room URL
    DEEPGRAM_API_KEY: Deepgram STT API key
    CARTESIA_API_KEY: Cartesia TTS API key
    BRAIN_API_URL: Brain API endpoint (default: http://localhost:8000)
"""

# Standard library imports
import asyncio
import base64
import io
import os
import sys
from typing import Optional

# Third-party imports
import aiohttp
import weave
from dotenv import load_dotenv
from loguru import logger
from PIL import Image

# Configure loguru - set to INFO for production, DEBUG for development
logger.remove()
logger.add(sys.stderr, level="INFO")

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams

from pipecat.frames.frames import (
    EndFrame,
    Frame,
    InputImageRawFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMMessagesFrame,
    TextFrame,
    TranscriptionFrame,
    TTSSpeakFrame,
)

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMAssistantAggregatorParams,
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.runner.types import DailyRunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyTransport, DailyParams
from pipecat.transports.daily.utils import DailyRESTHelper, DailyRoomParams

load_dotenv(override=True)

# Initialize Weave
# weave.init("gcp-assistant-rag")

# Configuration
BRAIN_API_URL = os.getenv("BRAIN_API_URL", "http://localhost:8000")

class ScreenShareCaptureProcessor(FrameProcessor):
    """
    Processor to capture incoming screen share frames and store them
    as JPEG base64 strings for the Brain API.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._latest_frame_base64: Optional[str] = None
        self._lock = asyncio.Lock()
        self._audio_frame_count = 0 # For sampled logging
    
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        from pipecat.frames.frames import UserAudioRawFrame, SystemFrame, TranscriptionFrame, LLMMessagesFrame
        
        # Sampled audio logging to confirm ingress
        if isinstance(frame, UserAudioRawFrame):
            self._audio_frame_count += 1
            if self._audio_frame_count % 100 == 0:
                logger.debug(f"🔊 [ScreenShareCapture] Received 100 audio frames (total: {self._audio_frame_count})")

        # High-frequency logging (only for non-audio frames to avoid spam)
        if not isinstance(frame, (UserAudioRawFrame, SystemFrame)):
            logger.debug(f"🔍 [ScreenShareCapture] Frame In: {frame}")

        # CRITICAL: Always propagate frame immediately to prevent deadlocks
        # super().process_frame pushes the frame, so we don't call self.push_frame at the end.
        await super().process_frame(frame, direction)
        
        # In Daily, screen share comes as InputImageRawFrame
        if isinstance(frame, InputImageRawFrame):
            async with self._lock:
                try:
                    image = Image.frombytes("RGB", frame.size, frame.image)
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=70)
                    self._latest_frame_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                except Exception as e:
                    logger.error(f"Error processing video frame: {e}")

    async def get_latest_frame_base64(self) -> Optional[str]:
        async with self._lock:
            return self._latest_frame_base64

class BrainProcessor(FrameProcessor):
    """
    Main logic processor that calls the /assist RAG backend.
    """
    def __init__(self, screen_capture: ScreenShareCaptureProcessor, context: LLMContext, **kwargs):
        super().__init__(**kwargs)
        self._screen_capture = screen_capture
        self._context = context
        self._session: Optional[aiohttp.ClientSession] = None
        self._ready = False # Startup gate
    
    def set_ready(self):
        self._ready = True
        logger.info("🚀 BrainProcessor is now READY and gaters are open")

    async def cleanup(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _ensure_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        from pipecat.frames.frames import (
            CancelFrame, EndFrame, TranscriptionFrame, 
            StartFrame, UserAudioRawFrame, SystemFrame,
            UserSpeakingFrame, UserStoppedSpeakingFrame
        )

        # Tracing for ALL relevant frames
        if not isinstance(frame, (UserAudioRawFrame, SystemFrame)):
            logger.debug(f"📥 [BrainProcessor] Received frame: {frame}")

        # CRITICAL: Always propagate frame immediately via super().process_frame
        await super().process_frame(frame, direction)
        
        # Diagnostic logging for transcriptions
        if isinstance(frame, TranscriptionFrame):
            log_msg = f"🎙️ Transcription ({'FINAL' if frame.user else 'INTERIM'}): {frame.text}"
            logger.info(log_msg)

        if isinstance(frame, StartFrame):
            self._ready = False # Reset on new start
            return

        if isinstance(frame, (CancelFrame, EndFrame)):
            await self.cleanup()
            return

        if isinstance(frame, LLMMessagesFrame):
            logger.info(f"📬 [BrainProcessor] Received LLMMessagesFrame (Ready={self._ready})")
            if not self._ready:
                logger.warning("⏳ BrainProcessor ignoring frame - waiting for on_participant_joined")
                return

            messages = self._context.get_messages()
            if not messages: return
            
            transcript = messages[-1].get("content", "").strip()
            
            if transcript:
                logger.info(f"🎤 Brain processing transcript in background: '{transcript}'")
                # Run API call in background so we don't block the processor task
                self.create_task(self._process_transcript(transcript, direction))
            return

    async def _process_transcript(self, transcript: str, direction: FrameDirection):
        screen_base64 = await self._screen_capture.get_latest_frame_base64()
        
        try:
            # Short timeout to keep system alive
            response_text = await asyncio.wait_for(
                self._call_brain_api(transcript, screen_base64),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("⏳ Brain API timed out")
            response_text = "Sorry, I'm taking too long to think. Can you repeat that?"
        except Exception as e:
            logger.error(f"Error in brain processing task: {e}")
            response_text = "I hit a snag while thinking. One moment."

        if response_text:
            logger.info(f"🧠 Brain response ready: {response_text[:50]}...")
            self._context.add_message({"role": "assistant", "content": response_text})
            
            # Push TextFrame for TTS and UI visibility
            await self.push_frame(LLMFullResponseStartFrame(), direction)
            await self.push_frame(TextFrame(response_text), direction)
            await self.push_frame(LLMFullResponseEndFrame(), direction)

    @weave.op()
    async def _call_brain_api(self, transcript: str, screenshot_base64: Optional[str] = None) -> Optional[str]:
        await self._ensure_session()
        try:
            # Use short timeout in aiohttp
            timeout = aiohttp.ClientTimeout(total=4.5)
            async with self._session.post(
                f"{BRAIN_API_URL}/assist",
                json={"transcript": transcript, "screenshot": screenshot_base64 or ""},
                timeout=timeout
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    steps = [f"Step {s['step']}: {s['text']}" for s in data.get("instructions", []) if s.get("text")]
                    return " ".join(steps) if steps else "I couldn't find specific instructions for that."
                return f"Brain API Error: {resp.status}"
        except Exception as e:
            logger.error(f"Brain API connection error: {e}")
            return "Connection error with the brain."

async def run_bot(transport: BaseTransport):
    # 1. Setup Services
    stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="71a7ad14-091c-4e8e-a314-022ece01c121", # British Lady
    )

    # 2. Setup Processors
    screen_capture = ScreenShareCaptureProcessor()
    context = LLMContext([
        {"role": "system", "content": "You are a GCP Assistant. You help users navigate the GCP console based on screenshots and voice commands."}
    ])
    context_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.3))
        ),
    )
    brain = BrainProcessor(screen_capture, context)

    # 3. Pipeline Construction
    pipeline = Pipeline([
        transport.input(),
        screen_capture,
        stt,
        context_aggregator.user(),
        brain,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True, enable_metrics=True))

    @transport.event_handler("on_participant_joined")
    async def on_participant_joined(transport, participant):
        logger.info(f"✅ Participant joined: {participant['id']}")
        
        # 1.0s buffer to avoid Daily startup race condition
        await asyncio.sleep(1.0)
        
        greeting = "Hello! I'm your GCP Assistant. Share your screen and let's get started."
        context.add_message({"role": "assistant", "content": greeting})
        
        # Queue TextFrame for the initial greeting
        await task.queue_frames([
            LLMFullResponseStartFrame(),
            TextFrame(greeting),
            LLMFullResponseEndFrame()
        ])
        
        # Enable the brain ONLY after greeting is queued
        brain.set_ready()

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await brain.cleanup()
        await task.cancel()

    runner = PipelineRunner()
    await runner.run(task)

async def main():
    # 1. Verify API Keys
    cartesia_key = os.getenv("CARTESIA_API_KEY")
    if cartesia_key:
        print(f"🔑 Cartesia API Key loaded: {cartesia_key[:5]}...{cartesia_key[-5:]}")
    else:
        logger.error("❌ CARTESIA_API_KEY not found in .env")

    # 2. Check for Static Room URL
    room_url = os.getenv("DAILY_SAMPLE_ROOM_URL")
    
    if room_url:
        logger.info(f"🔗 Connecting to STATIC room: {room_url}")
    else:
        # 3. Fallback to Dynamic Room Creation
        api_key = os.getenv("DAILY_API_KEY")
        if not api_key:
            logger.error("❌ Neither DAILY_SAMPLE_ROOM_URL nor DAILY_API_KEY found in .env.")
            return

        async with aiohttp.ClientSession() as session:
            # Use DailyRESTHelper to create a room
            helper = DailyRESTHelper(
                daily_api_key=api_key,
                aiohttp_session=session
            )
            try:
                # Create room with default params
                room = await helper.create_room(DailyRoomParams())
                room_url = room.url
                logger.info(f"✨ Created dynamic room: {room_url}")
            except Exception as e:
                logger.error(f"❌ Failed to create room: {e}")
                return

    # Use DailyRunnerArguments to support automated room management
    runner_args = DailyRunnerArguments(room_url=room_url)
    
    transport_params = {
        "daily": lambda: DailyParams(
            audio_out_enabled=True,
            audio_in_enabled=True,
            video_out_enabled=True,
            video_in_enabled=True,
        ),
    }
    
    transport = await create_transport(runner_args, transport_params)
    
    if isinstance(transport, DailyTransport):
        print(f"\n🚀 Bot starting in Daily Room: {transport.room_url}")
        print(f"👉 Open this URL in your browser: {transport.room_url}\n")
        
    await run_bot(transport)

if __name__ == "__main__":
    asyncio.run(main())
