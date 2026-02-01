"""
Pipecat service initialization
Factory functions for STT, LLM, and TTS services
"""

import logging
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.cartesia.tts import CartesiaTTSService

from .config import (
    DEEPGRAM_API_KEY,
    OPENAI_API_KEY,
    CARTESIA_API_KEY,
    STT_MODEL,
    LLM_MODEL,
    TTS_MODEL,
    TTS_VOICE,
    SAMPLE_RATE,
)
from .rag import build_system_prompt
from .config import SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# ============================================
# SPEECH-TO-TEXT SERVICE
# ============================================

def create_stt_service() -> DeepgramSTTService:
    """
    Create and configure Deepgram STT service
    """
    service = DeepgramSTTService(
        api_key=DEEPGRAM_API_KEY,
        model=STT_MODEL,
    )
    
    logger.info(f"✓ STT service created: Deepgram {STT_MODEL}")
    return service


# ============================================
# LANGUAGE MODEL SERVICE
# ============================================

def create_llm_service() -> OpenAILLMService:
    """
    Create and configure OpenAI LLM service
    """
    service = OpenAILLMService(
        api_key=OPENAI_API_KEY,
        model=LLM_MODEL,
    )
    
    logger.info(f"✓ LLM service created: {LLM_MODEL}")
    
    return service


# ============================================
# TEXT-TO-SPEECH SERVICE
# ============================================

def create_tts_service() -> CartesiaTTSService:
    """
    Create and configure TTS service
    """
    # Cartesia service initialization
    service = CartesiaTTSService(
        api_key=CARTESIA_API_KEY,
        voice_id=TTS_VOICE,
        model_id=TTS_MODEL,
    )
    logger.info(f"✓ TTS service created: Cartesia ({TTS_MODEL})")
    
    return service
