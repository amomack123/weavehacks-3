"""
Logging utilities for conversation tracking and metrics
JSONL-based structured logging
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .config import LOGS_DIR
from .rag import get_rag_context

logger = logging.getLogger(__name__)

# ============================================
# CONVERSATION LOGGER
# ============================================

class ConversationLogger:
    """Handles structured logging of conversation turns"""
    
    def __init__(self, logs_dir: Path = LOGS_DIR):
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(exist_ok=True)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"Conversation logger initialized: session {self.session_id}")
    
    def log_turn(self, user_text: str, agent_text: str, metadata: Optional[Dict] = None):
        """
        Log a conversation turn with metadata
        
        Args:
            user_text: User's input text
            agent_text: Agent's response text
            metadata: Optional additional metadata
        """
        log_entry = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "user": user_text,
            "agent": agent_text,
            "rag_context_length": len(get_rag_context()),
            "metadata": metadata or {}
        }
        
        log_file = self.logs_dir / f"conversation_{datetime.now().date()}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        logger.debug(f"Logged conversation turn to {log_file}")
    
    def log_event(self, event_type: str, data: Dict):
        """
        Log system events (errors, interruptions, etc.)
        
        Args:
            event_type: Type of event (e.g., "error", "interruption", "participant_joined")
            data: Event data dictionary
        """
        log_entry = {
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        log_file = self.logs_dir / f"events_{datetime.now().date()}.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        logger.debug(f"Logged event '{event_type}' to {log_file}")


# ============================================
# GLOBAL LOGGER INSTANCE
# ============================================

# Single global conversation logger instance
conversation_logger = ConversationLogger()
