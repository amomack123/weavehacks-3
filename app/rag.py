"""
Dynamic RAG context management
Global context variable with thread-safe updates
"""

import threading
import logging

logger = logging.getLogger(__name__)

# ============================================
# GLOBAL RAG CONTEXT
# ============================================

# Global variable holding current RAG context
current_rag_context: str = ""

# Thread-safe lock for context updates
_rag_context_lock = threading.Lock()

# ============================================
# PUBLIC API
# ============================================

def update_rag_context(new_context: str) -> None:
    """
    Update the global RAG context (thread-safe)
    
    Args:
        new_context: New context string to inject into LLM prompts
    """
    global current_rag_context
    
    with _rag_context_lock:
        old_length = len(current_rag_context)
        current_rag_context = new_context
        logger.info(f"RAG context updated: {old_length} → {len(new_context)} chars")

def get_rag_context() -> str:
    """Get current RAG context (thread-safe)"""
    with _rag_context_lock:
        return current_rag_context

def clear_rag_context() -> None:
    """Clear the RAG context"""
    update_rag_context("")

def update_reward_store(state_key: str, reward: float):
    """
    Update the episodic reward store based on user behavioral feedback
    """
    logger.info(f"Episodic memory updated for {state_key}: Reward {reward}")
    # TODO: redis.hincrby("rewards", state_key, reward)

def get_current_screen_hash() -> str:
    """Hook to get the latest vision-based screen identifier"""
    # Placeholder for vision team logic
    return "current_screen_sha256"

def build_system_prompt(template: str) -> str:
    """
    Final Aggregator: Combine Knowledge (RAG) + Episodic Memory (RL)
    """
    # 1. Get Domain Knowledge (from Redis Vector Search)
    domain_knowledge = get_rag_context()
    
    # 2. Get Episodic Knowledge (Placeholder for learned success)
    # screen_hash = get_current_screen_hash()
    # In production, this pulls from Redis based on intent + screen_hash
    best_move = "Coord(450, 200)"
    
    episodic_memory = f"LEARNED STRATEGY: Historically, coordinate {best_move} was successful here."
    
    if not domain_knowledge or domain_knowledge.strip() == "":
        domain_knowledge = "No specific context provided."
    
    # 3. Inject Combined Intelligence into Template
    context_block = f"{domain_knowledge}\n\n{episodic_memory}"
    
    prompt = template.format(rag_context=context_block)
    logger.debug("Successfully aggregated RAG + RL for System Prompt")
    
    return prompt
