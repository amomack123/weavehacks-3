"""
Pipecat event handlers
Handles frame events: text_frame, tts_request, interruptions, etc.
"""

import logging
from typing import Optional

from .logging_utils import conversation_logger
from .rag import build_system_prompt, get_rag_context
from .config import SYSTEM_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

# ============================================
# CONVERSATION STATE TRACKING
# ============================================

class ConversationState:
    """
    Tracks current conversation turn state
    Note: Pipecat manages chat history internally, 
    this is just for logging purposes
    """
    def __init__(self):
        self.current_user_text = ""
        self.current_agent_text = ""
    
    def set_user_text(self, text: str):
        """Set current user input"""
        self.current_user_text = text
    
    def set_agent_text(self, text: str):
        """Set current agent response"""
        self.current_agent_text = text
    
    def log_turn(self):
        """Log conversation turn if both user and agent text exist"""
        if self.current_user_text and self.current_agent_text:
            conversation_logger.log_turn(
                self.current_user_text,
                self.current_agent_text,
                metadata={
                    "rag_context_preview": get_rag_context()[:100]
                }
            )
            # Clear for next turn
            self.current_user_text = ""
            self.current_agent_text = ""


# Global conversation state
_conversation_state = ConversationState()


# ============================================
# EVENT HANDLER REGISTRATION
# ============================================

def register_handlers(pipeline, llm_service):
    """
    Register all Pipecat event handlers
    
    Args:
        pipeline: Pipecat Pipeline instance
        llm_service: OpenAI LLM service instance (for dynamic prompt updates)
    """
    
    @pipeline.event_handler("on_first_participant_joined")
    async def on_participant_joined(pipeline, participant):
        """Triggered when first user joins"""
        logger.info(f"✓ Participant joined: {participant}")
        conversation_logger.log_event("participant_joined", {
            "participant": str(participant)
        })
        
        # Optional: Send welcome message
        # from pipecat.frames.frames import TextFrame
        # await pipeline.queue_frame(TextFrame("Hello! How can I help you today?"))
    
    
    @pipeline.event_handler("on_participant_left")
    async def on_participant_left(pipeline, participant):
        """Triggered when user disconnects"""
        logger.info(f"Participant left: {participant}")
        conversation_logger.log_event("participant_left", {
            "participant": str(participant)
        })
    
    
    @pipeline.event_handler("on_text_message")
    async def on_text_message(pipeline, text: str, participant):
        """
        Triggered when STT produces final transcription
        
        This is where we inject updated RAG context into the system prompt
        per-request without recreating the LLM service
        """
        logger.info(f"[USER]: {text}")
        _conversation_state.set_user_text(text)
        
        # logger.debug("System prompt updated with current RAG context")
    
    
    @pipeline.event_handler("on_app_message")
    async def on_app_message(pipeline, message, sender):
        """Triggered when LLM generates response"""
        if isinstance(message, str):
            logger.info(f"[AGENT]: {message}")
            _conversation_state.set_agent_text(message)
            
            # Log conversation turn
            _conversation_state.log_turn()
    
    
    @pipeline.event_handler("on_interruption")
    async def on_interruption(pipeline):
        """Triggered when user interrupts agent speech"""
        logger.warning("⚠️  User interrupted - canceling current output")
        conversation_logger.log_event("interruption", {
            "interrupted_text": _conversation_state.current_agent_text
        })
        # Pipeline automatically handles cancellation
    
    
    @pipeline.event_handler("on_error")
    async def on_error(pipeline, error):
        """Triggered on pipeline errors"""
        logger.error(f"❌ Pipeline error: {error}")
        conversation_logger.log_event("error", {
            "error": str(error),
            "type": type(error).__name__
        })
    
    
    # Optional: Additional frame-level handlers for debugging
    
    # @pipeline.event_handler("on_audio_frame")
    # async def on_audio_frame(pipeline, frame):
    #     """Triggered on incoming audio frames (verbose)"""
    #     logger.debug(f"Audio frame received: {len(frame.audio)} bytes")
    
    
    # @pipeline.event_handler("on_tts_request")
    # async def on_tts_request(pipeline, request):
    #     """Triggered when LLM outputs text for TTS"""
    #     logger.debug(f"TTS request: {request.text[:50]}...")
    
    
    # @pipeline.event_handler("on_tts_response")
    # async def on_tts_response(pipeline, response):
    #     """Triggered when TTS generates audio"""
    #     logger.debug(f"TTS response: {len(response.audio)} bytes")
    
    
    logger.info("✓ Event handlers registered")
