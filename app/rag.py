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

def build_system_prompt(template: str, user_query: str = "") -> str:
    """
    Final Aggregator: Combine Knowledge (RAG) + Episodic Memory (RL)
    
    Args:
        template: System prompt template with {rag_context} placeholder
        user_query: Optional user query for vector search (if empty, uses global context)
    """
    from .redis_client import query_knowledge_base, get_learned_action
    
    # 1. Get Domain Knowledge from Redis Vector Search
    if user_query:
        # Use vector search for specific query
        domain_knowledge = query_knowledge_base(user_query, top_k=2)
    else:
        # Fall back to global RAG context
        domain_knowledge = get_rag_context()
    
    if not domain_knowledge or domain_knowledge.strip() == "":
        domain_knowledge = "No specific context provided."
    
    # 2. Get Episodic Knowledge (Learned Actions from RL)
    # Note: This requires screen_hash and intent from the current conversation context
    # For now, we use a placeholder. In production, you would:
    # - Get screen_hash from vision_hooks.hash_screen()
    # - Extract intent from the LLM's understanding
    
    episodic_memory = ""
    try:
        # Example: get_learned_action(screen_hash, intent)
        # best_action = get_learned_action("current_hash", "user_intent")
        # if best_action:
        #     episodic_memory = f"LEARNED STRATEGY: Click target {best_action['best_mask_id']} (confidence: {best_action['score']:.2f})"
        
        # Placeholder until we wire screen capture + intent extraction
        episodic_memory = "No learned strategies for this context yet."
    except Exception as e:
        logger.error(f"Failed to retrieve episodic memory: {e}")
        episodic_memory = ""
    
    # 3. Inject Combined Intelligence into Template
    context_block = f"{domain_knowledge}\n\n{episodic_memory}" if episodic_memory else domain_knowledge
    
    prompt = template.format(rag_context=context_block)
    logger.debug("Successfully aggregated RAG + RL for System Prompt")
    
    return prompt
