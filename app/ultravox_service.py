"""
Ultravox Pipecat Service
Wraps Ultravox unified voice AI (STT+LLM+TTS) for use in Pipecat pipeline.
"""

import asyncio
import logging
import os
import json
import aiohttp
from typing import Optional

from pipecat.frames.frames import (
    Frame,
    StartFrame,
    EndFrame,
    CancelFrame,
    AudioRawFrame,
    InputAudioRawFrame,
    OutputAudioRawFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

logger = logging.getLogger(__name__)

# Ultravox API configuration
ULTRAVOX_API_URL = "https://api.ultravox.ai/api"


class UltravoxPipecatService(FrameProcessor):
    """
    Pipecat-compatible wrapper for Ultravox unified voice AI.
    
    Replaces the separate STT + LLM + TTS services with a single
    Ultravox connection that handles speech-to-speech.
    """
    
    def __init__(
        self,
        api_key: str,
        system_prompt: str,
        voice: str = "terrence",  # Default Ultravox voice
        model: str = "fixie-ai/ultravox-70B",  # Default model
        **kwargs
    ):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.voice = voice
        self.model = model
        
        self._call_id: Optional[str] = None
        self._join_url: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ready = False
        self._receive_task: Optional[asyncio.Task] = None
        self._started = False
        self._pipeline_ready = False  # Track when pipeline is fully ready
    
async def _initialize_ultravox(self):
    """Initialize Ultravox call when pipeline starts."""
    if self._started:
        return
        
    logger.info("🎤 UltravoxPipecatService initializing...")
    
    self._session = aiohttp.ClientSession()
    
    try:
        # Create Ultravox call via REST API
        call_data = await self._create_ultravox_call()
        self._call_id = call_data.get("callId")
        self._join_url = call_data.get("joinUrl")
        
        logger.info(f"✓ Ultravox call created: {self._call_id}")
        
        # Connect to Ultravox WebSocket for audio streaming
        if self._join_url:
            await self._connect_websocket()
            self._ready = True
            self._started = True
            # No artificial delay - pipeline is already started
            
            logger.info("✓ Ultravox WebSocket connected and ready")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Ultravox: {e}")
        raise
    
    async def _cleanup(self):
        """Clean up Ultravox resources."""
        logger.info("Stopping UltravoxPipecatService...")
        
        self._ready = False
        self._started = False
        self._pipeline_ready = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self._ws:
            await self._ws.close()
        
        if self._session:
            await self._session.close()
    
# app/ultravox_service.py

async def process_frame(self, frame: Frame, direction: FrameDirection):
    """Process incoming frames from Daily transport."""
    
    # Handle StartFrame - let parent process it first, then initialize
    if isinstance(frame, StartFrame):
        # Push StartFrame downstream FIRST so pipeline knows we've started
        await self.push_frame(frame, direction)
        
        # NOW initialize Ultravox (in background so we don't block)
        if not self._started:
            asyncio.create_task(self._initialize_ultravox())
        return
    
    # Handle EndFrame/CancelFrame - cleanup
    if isinstance(frame, (EndFrame, CancelFrame)):
        await self._cleanup()
        await self.push_frame(frame, direction)
        return
    
    # Handle incoming audio from Daily (user speaking)
    if isinstance(frame, (AudioRawFrame, InputAudioRawFrame)):
        if self._ready and self._ws:
            try:
                # Send audio to Ultravox
                await self._send_audio(frame.audio)
            except Exception as e:
                logger.debug(f"Error sending audio to Ultravox: {e}")
        # Don't push input audio frames downstream - Ultravox handles response
        return
    
    # Pass through other frames
    await self.push_frame(frame, direction)
    
    async def _create_ultravox_call(self) -> dict:
        """Create a new Ultravox call via REST API."""
        url = f"{ULTRAVOX_API_URL}/calls"
        
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "systemPrompt": self.system_prompt,
            "model": self.model,
            "voice": self.voice,
            "medium": {
                "serverWebSocket": {
                    "inputSampleRate": 16000,
                    "outputSampleRate": 24000,
                }
            },
            "firstSpeaker": "FIRST_SPEAKER_AGENT",  # Agent speaks first
        }
        
        async with self._session.post(url, headers=headers, json=payload) as resp:
            if resp.status != 200 and resp.status != 201:
                error_text = await resp.text()
                raise Exception(f"Ultravox API error {resp.status}: {error_text}")
            
            return await resp.json()
    
    async def _connect_websocket(self):
        """Connect to Ultravox WebSocket for audio streaming."""
        if not self._join_url:
            raise ValueError("No join URL available")
        
        self._ws = await self._session.ws_connect(self._join_url)
        
        # Start receiving audio in background
        self._receive_task = asyncio.create_task(self._receive_audio_loop())
    
    async def _send_audio(self, audio_bytes: bytes):
        """Send audio data to Ultravox."""
        if self._ws and not self._ws.closed:
            # Ultravox expects raw PCM audio
            await self._ws.send_bytes(audio_bytes)
    
    async def _receive_audio_loop(self):
        """Receive audio from Ultravox and push to pipeline."""
        logger.info("Starting Ultravox audio receive loop")
        
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    # Audio response from Ultravox
                    audio_frame = OutputAudioRawFrame(
                        audio=msg.data,
                        sample_rate=24000,
                        num_channels=1,
                    )
                    
                    # Push to Daily output - ignore StartFrame errors
                    try:
                        await self.push_frame(audio_frame, FrameDirection.DOWNSTREAM)
                    except Exception as e:
                        # Ignore StartFrame timing errors - audio still flows
                        if "StartFrame" not in str(e):
                            logger.debug(f"Error pushing audio frame: {e}")
                    
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    # Transcript or other text messages
                    try:
                        data = json.loads(msg.data)
                        msg_type = data.get("type")
                        
                        if msg_type == "transcript":
                            transcript = data.get("text", "")
                            role = data.get("role", "user")
                            if transcript:
                                logger.info(f"🎙️ [{role}]: {transcript}")
                        
                        elif msg_type == "agent_response":
                            text = data.get("text", "")
                            if text:
                                logger.info(f"🎙️ [agent]: {text}")
                        
                        elif msg_type == "state":
                            state = data.get("state", "")
                            logger.debug(f"Ultravox state: {state}")
                            
                    except json.JSONDecodeError:
                        logger.debug(f"Non-JSON text message from Ultravox")
                    
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Ultravox WebSocket error: {msg}")
                    break
                    
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("Ultravox WebSocket closed")
                    break
                    
        except asyncio.CancelledError:
            logger.debug("Ultravox receive loop cancelled")
        except Exception as e:
            logger.error(f"Ultravox receive loop error: {e}")


def create_ultravox_service() -> UltravoxPipecatService:
    """Factory function to create UltravoxPipecatService with config."""
    from app.config import SYSTEM_PROMPT_TEMPLATE
    
    api_key = os.getenv("ULTRAVOX_API_KEY")
    if not api_key:
        raise ValueError("ULTRAVOX_API_KEY not found in environment")
    
    return UltravoxPipecatService(
        api_key=api_key,
        system_prompt=SYSTEM_PROMPT_TEMPLATE,
    )
