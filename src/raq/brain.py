"""
Brain module for GCP Assistant: Retrieval and RL Reward System.

This module provides:
1. retrieve_iam_steps() - RAG retrieval from Redis vector index
2. generate_screen_hash() - Perceptual hashing for screen recognition
3. update_reward() - RL reward tracking with screen_hash + intent
4. get_best_action() - Get the best sam_mask_id for a given screen/intent

All functions are wrapped with @weave.op() for W&B observability.

Environment Variables:
    GOOGLE_API_KEY: Gemini API key
    REDIS_URL: Redis connection URL (default: redis://localhost:6379)
    WANDB_API_KEY: Weights & Biases API key for Weave
"""

# Standard library imports
import io
import os
from typing import Optional, Union

# Third-party imports
import imagehash
import numpy as np
import redis
import weave
from PIL import Image
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

# Load environment variables
load_dotenv()

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
INDEX_NAME = "iam_rules"
KNOWLEDGE_PREFIX = "kg:gcp:iam:"

# Initialize Weave for observability
# weave.init("gcp-assistant-rag")


# =============================================================================
# Redis Connection
# =============================================================================

def _get_redis_client() -> redis.Redis:
    """Get a Redis client connection with string decoding."""
    return redis.from_url(REDIS_URL, decode_responses=True)


# =============================================================================
# Screen Hashing (The Eyes)
# =============================================================================

@weave.op()
def generate_screen_hash(image_frame: Union[bytes, Image.Image, str]) -> str:
    """
    Generate a perceptual hash (phash) for a screen frame.
    
    Uses the imagehash library's perceptual hashing algorithm (phash) which
    creates a fingerprint of the image based on its visual structure. This
    allows recognition of the 'same' screen even with minor pixel differences
    (cursor position, slight rendering variations, anti-aliasing).
    
    The hash is robust to:
    - Small color changes
    - Minor geometric transformations
    - Compression artifacts
    
    Args:
        image_frame: Can be:
            - bytes: Raw image data (JPEG/PNG)
            - PIL.Image: A PIL Image object
            - str: Base64 encoded image string
    
    Returns:
        str: The perceptual hash as a 16-character hex string
    
    Example:
        >>> from PIL import Image
        >>> img = Image.new("RGB", (1280, 720), color=(100, 100, 100))
        >>> hash_str = generate_screen_hash(img)
        >>> print(hash_str)  # e.g., "8000000000000000"
    """
    # Convert input to PIL Image
    if isinstance(image_frame, bytes):
        image = Image.open(io.BytesIO(image_frame))
    elif isinstance(image_frame, str):
        import base64
        image_bytes = base64.b64decode(image_frame)
        image = Image.open(io.BytesIO(image_bytes))
    elif isinstance(image_frame, Image.Image):
        image = image_frame
    else:
        raise ValueError(f"Unsupported image_frame type: {type(image_frame)}")
    
    # Generate perceptual hash
    phash = imagehash.phash(image)
    return str(phash)


# =============================================================================
# RL Reward Store (The Memory)
# =============================================================================

@weave.op()
def update_reward(
    screen_hash: str,
    intent: str,
    sam_mask_id: str,
    reward_value: float
) -> dict:
    """
    Atomically update the reward score for a clickable region.
    
    Uses Redis HINCRBYFLOAT for atomic float increment operations, ensuring
    thread-safe updates even under concurrent access. The reward is stored
    in a Redis Hash with the pattern:
    
        Key:   rewards:{screen_hash}:{intent}
        Field: {sam_mask_id}
        Value: cumulative score (float)
    
    This implements a simple RL feedback loop where positive rewards reinforce
    good click targets and negative rewards discourage bad ones.
    
    Args:
        screen_hash: Perceptual hash of the screen state (from generate_screen_hash)
        intent: User's intent/action (e.g., 'create_bucket', 'delete_vm')
        sam_mask_id: Identifier for the clickable region (use normalized 0.0-1.0 coords)
        reward_value: Delta to add to the cumulative score (can be negative)
    
    Returns:
        dict: Contains 'key', 'sam_mask_id', 'reward_delta', and 'new_score'
    
    Example:
        >>> update_reward("8000000000000000", "create_bucket", "mask_001", 1.0)
        {'key': 'rewards:8000000000000000:create_bucket', 'sam_mask_id': 'mask_001', ...}
    """
    r = _get_redis_client()
    key = f"rewards:{screen_hash}:{intent}"
    new_score = r.hincrbyfloat(key, sam_mask_id, reward_value)
    
    return {
        "key": key,
        "sam_mask_id": sam_mask_id,
        "reward_delta": reward_value,
        "new_score": new_score
    }


@weave.op()
def get_best_action(screen_hash: str, intent: str) -> Optional[dict]:
    """
    Retrieve the sam_mask_id with the highest cumulative reward.
    
    Queries the Redis Hash for all stored rewards for the given screen/intent
    combination and returns the action with the maximum score.
    
    Args:
        screen_hash: Perceptual hash of the screen state
        intent: User's intent/action
    
    Returns:
        dict: Contains 'best_mask_id', 'score', and 'all_actions', or None if no data
    
    Example:
        >>> result = get_best_action("8000000000000000", "create_bucket")
        >>> print(result['best_mask_id'])  # e.g., "mask_001"
    """
    r = _get_redis_client()
    key = f"rewards:{screen_hash}:{intent}"
    scores = r.hgetall(key)
    
    if not scores:
        return None
    
    best_mask_id = None
    max_score = float('-inf')
    
    for mask_id, score_str in scores.items():
        score = float(score_str)
        if score > max_score:
            max_score = score
            best_mask_id = mask_id
    
    return {
        "screen_hash": screen_hash,
        "intent": intent,
        "best_mask_id": best_mask_id,
        "score": max_score,
        "all_actions": {k: float(v) for k, v in scores.items()}
    }


# =============================================================================
# RAG Retrieval (Knowledge Base)
# =============================================================================

def _get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Get the Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )


def _get_search_index() -> SearchIndex:
    """Get the Redis search index for IAM knowledge."""
    schema = IndexSchema.from_dict({
        "index": {
            "name": INDEX_NAME,
            "prefix": KNOWLEDGE_PREFIX,
            "storage_type": "hash"
        },
        "fields": [
            {"name": "content", "type": "text"},
            {"name": "category", "type": "tag"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "algorithm": "flat",
                    "dims": 768,
                    "distance_metric": "cosine",
                    "datatype": "float32"
                }
            }
        ]
    })
    return SearchIndex(schema, redis_url=REDIS_URL)


@weave.op()
def retrieve_iam_steps(transcript: str, top_k: int = 2) -> dict:
    """
    Retrieve relevant IAM steps from Redis based on voice transcript.
    
    Args:
        transcript: The user's voice transcript query
        top_k: Number of results to return (default: 2)
    
    Returns:
        dict: Contains 'query' and 'results' list with text and similarity scores
    """
    embeddings_model = _get_embeddings_model()
    query_embedding = embeddings_model.embed_query(transcript)
    query_vector = np.array(query_embedding, dtype=np.float32).tobytes()
    
    query = VectorQuery(
        vector=query_vector,
        vector_field_name="embedding",
        return_fields=["content", "category"],
        num_results=top_k
    )
    
    index = _get_search_index()
    results = index.query(query)
    
    parsed_results = []
    for result in results:
        parsed_results.append({
            "text": result.get("content", ""),
            "category": result.get("category", ""),
            "similarity": 1 - float(result.get("vector_distance", 1))
        })
    
    return {
        "query": transcript,
        "results": parsed_results
    }


# =============================================================================
# Module Test (commented out for production imports)
# =============================================================================

# if __name__ == "__main__":
#     from PIL import Image
#     
#     print("Testing Brain module...")
#     
#     # Test screen hashing
#     dummy_image = Image.new("RGB", (1280, 720), color=(100, 100, 100))
#     screen_hash = generate_screen_hash(dummy_image)
#     print(f"Generated phash: {screen_hash}")
#     
#     # Test reward updates
#     update_reward(screen_hash, "create_bucket", "mask_001", 1.0)
#     
#     # Test best action
#     best = get_best_action(screen_hash, "create_bucket")
#     print(f"Best action: {best}")
#     
#     # Test RAG retrieval
#     result = retrieve_iam_steps("how do I grant access")
#     print(f"Found {len(result['results'])} chunks")
