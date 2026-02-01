"""
Pipecat pipeline assembly
Creates and wires together the full STT → LLM → TTS pipeline
"""

import logging
from urllib.parse import urlparse
from pipecat.pipeline.pipeline import Pipeline
from pipecat.transports.websocket.server import WebsocketServerTransport, WebsocketServerParams

from .config import WEBSOCKET_URL, SAMPLE_RATE, CHANNELS
from .services import create_stt_service, create_llm_service, create_tts_service
from .handlers import register_handlers
from .processors import RewardProcessor

logger = logging.getLogger(__name__)

# ============================================
# PIPELINE CREATION
# ============================================

def create_pipeline() -> Pipeline:
    """
    Create and configure the complete Pipecat pipeline
    
    Pipeline flow:
        WebSocket → STT → Reward Processor → LLM → TTS → WebSocket
    """
    logger.info("Creating Pipecat pipeline...")
    
    # Initialize services
    stt_service = create_stt_service()
    llm_service = create_llm_service()
    tts_service = create_tts_service()
    reward_processor = RewardProcessor()
    
    # Parse host/port from URL for WebsocketServerTransport
    parsed = urlparse(WEBSOCKET_URL)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8765
    
    # Configure transport params for Pipecat 0.0.x
    params = WebsocketServerParams(
        audio_out_enabled=True,
        audio_out_sample_rate=SAMPLE_RATE,
        audio_out_channels=CHANNELS,
        audio_in_enabled=True,
        audio_in_sample_rate=SAMPLE_RATE,
        audio_in_channels=CHANNELS,
    )
    
    # Create the Server transport
    transport = WebsocketServerTransport(
        params=params,
        host=host,
        port=port
    )
    
    logger.info(f"✓ WebSocket server configured to listen on: {host}:{port}")
    
    # Assemble pipeline stages
    # Flow: WebSocket → STT → Reward Processor → LLM → TTS → WebSocket
    pipeline = Pipeline(
        [
            transport.input(),   # Audio input from WebSocket
            stt_service,         # Speech-to-Text (Deepgram)
            reward_processor,    # Behavioral learning & Reward logic
            llm_service,         # Language Model (OpenAI)
            tts_service,         # Text-to-Speech (Cartesia/Silero)
            transport.output(),  # Audio output to WebSocket
        ]
    )
    
    # Register event handlers
    # Pass llm_service for dynamic prompt updates
    register_handlers(pipeline, llm_service)
    
    logger.info("✓ Pipeline created successfully")
    logger.info("Pipeline stages: WebSocket → STT → Reward → LLM → TTS → WebSocket")
    
    return pipeline
