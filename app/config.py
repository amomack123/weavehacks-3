"""
Configuration management for Pipecat Voice Agent
Loads environment variables and defines constants
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================
# API KEYS
# ============================================

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CARTESIA_API_KEY = os.getenv("CARTESIA_API_KEY")
DAILY_API_KEY = os.getenv("DAILY_API_KEY")  # For Daily Transport

# ============================================
# DAILY TRANSPORT CONFIGURATION
# ============================================

DAILY_ROOM_URL = os.getenv("DAILY_ROOM_URL")  # Set at runtime when creating room
DAILY_BOT_NAME = os.getenv("DAILY_BOT_NAME", "GCP Assistant")

# ============================================
# MODEL CONFIGURATION
# ============================================

# Speech-to-Text
STT_MODEL = os.getenv("STT_MODEL", "nova-2")

# Language Model
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Text-to-Speech
TTS_MODEL = os.getenv("TTS_MODEL", "sonic-english")
TTS_VOICE = os.getenv("TTS_VOICE", "79a125e8-cd45-4c13-8a67-188112f4dd22")

# ============================================
# AUDIO SETTINGS
# ============================================

SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "24000"))
CHANNELS = 1
ENCODING = "linear16"

# ============================================
# LLM PARAMETERS
# ============================================

LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "150"))

# ============================================
# LOGGING CONFIGURATION
# ============================================

LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))
LOGS_DIR.mkdir(exist_ok=True)

# ============================================
# SYSTEM PROMPT TEMPLATE
# ============================================

SYSTEM_PROMPT_TEMPLATE = """You are a helpful AI assistant with access to specialized knowledge.

Current Context:
{rag_context}

Instructions:
- Use the provided context to answer questions accurately
- If the context is empty or irrelevant, rely on your general knowledge
- Be conversational and natural in your responses
- Keep responses concise (2-3 sentences unless more detail is requested)
- If you don't know something, say so honestly
- Maintain a friendly, professional tone

Remember: You are in a voice conversation, so keep your answers brief and easy to understand when spoken aloud.
"""

# ============================================
# VALIDATION
# ============================================

def validate_config():
    """Validate required configuration"""
    errors = []
    
    if not DEEPGRAM_API_KEY:
        errors.append("DEEPGRAM_API_KEY not set")
    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not set")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    return True
