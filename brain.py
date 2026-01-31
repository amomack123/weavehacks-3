"""
Brain module for GCP Assistant: Retrieval and RL Reward System.

This module provides:
1. retrieve_iam_steps() - RAG retrieval from Redis vector index
2. update_step_reward() - RL reward tracking in Redis
3. get_step_stats() - Query reward statistics

All functions are wrapped with @weave.op() for W&B observability.

Usage:
    from brain import retrieve_iam_steps, update_step_reward

Environment Variables:
    GOOGLE_API_KEY: Gemini API key
    REDIS_URL: Redis connection URL (default: redis://localhost:6379)
    WANDB_API_KEY: Weights & Biases API key for Weave
"""

import os
from typing import Optional

import numpy as np
import redis
import weave
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

# Load environment variables
load_dotenv()

# Configuration - Dynamic Redis connection for Docker/local compatibility
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"
INDEX_NAME = "iam_knowledge"

# Initialize Weave for observability
weave.init("gcp-assistant-rag")


def _get_redis_client() -> redis.Redis:
    """Get a Redis client connection."""
    return redis.from_url(REDIS_URL, decode_responses=True)


def _get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Get the Gemini embeddings model."""
    return GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )


def _get_search_index() -> SearchIndex:
    """Get the Redis search index."""
    schema = IndexSchema.from_dict({
        "index": {
            "name": INDEX_NAME,
            "prefix": f"{INDEX_NAME}:",
            "storage_type": "hash"
        },
        "fields": [
            {"name": "text", "type": "text"},
            {"name": "chunk_id", "type": "tag"},
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
        dict with 'results' list containing text and similarity scores
    """
    print(f"🔍 Retrieving IAM steps for: '{transcript[:50]}...'")
    
    # Generate embedding for the query
    embeddings_model = _get_embeddings_model()
    query_embedding = embeddings_model.embed_query(transcript)
    query_vector = np.array(query_embedding, dtype=np.float32).tobytes()
    
    # Build vector query
    query = VectorQuery(
        vector=query_vector,
        vector_field_name="embedding",
        return_fields=["text", "chunk_id"],
        num_results=top_k
    )
    
    # Execute search
    index = _get_search_index()
    results = index.query(query)
    
    # Parse results
    parsed_results = []
    for result in results:
        parsed_results.append({
            "text": result.get("text", ""),
            "chunk_id": result.get("chunk_id", ""),
            "similarity": 1 - float(result.get("vector_distance", 1))  # Convert distance to similarity
        })
    
    print(f"✅ Found {len(parsed_results)} relevant chunks")
    
    return {
        "query": transcript,
        "results": parsed_results
    }


@weave.op()
def update_step_reward(task_id: str, success_status: bool) -> dict:
    """
    Update the reward counter for a task step using Redis HINCRBY.
    
    This implements a simple RL reward tracking system where each task
    has success/failure counters that can be used to measure learning progress.
    
    Args:
        task_id: Unique identifier for the task/step
        success_status: True for success, False for failure
    
    Returns:
        dict with updated counts
    """
    print(f"📊 Updating reward for task '{task_id}': {'success' if success_status else 'failure'}")
    
    r = _get_redis_client()
    key = f"rewards:{task_id}"
    
    field = "success" if success_status else "failure"
    new_count = r.hincrby(key, field, 1)
    
    # Get current stats
    stats = r.hgetall(key)
    
    result = {
        "task_id": task_id,
        "updated_field": field,
        "new_count": new_count,
        "success_count": int(stats.get("success", 0)),
        "failure_count": int(stats.get("failure", 0))
    }
    
    # Calculate success rate for observability
    total = result["success_count"] + result["failure_count"]
    result["success_rate"] = result["success_count"] / total if total > 0 else 0.0
    
    print(f"✅ Updated: success={result['success_count']}, failure={result['failure_count']}, rate={result['success_rate']:.2%}")
    
    return result


@weave.op()
def get_step_stats(task_id: str) -> dict:
    """
    Get current reward statistics for a task.
    
    Args:
        task_id: Unique identifier for the task/step
    
    Returns:
        dict with success/failure counts and success rate
    """
    r = _get_redis_client()
    key = f"rewards:{task_id}"
    
    stats = r.hgetall(key)
    
    success = int(stats.get("success", 0))
    failure = int(stats.get("failure", 0))
    total = success + failure
    
    return {
        "task_id": task_id,
        "success": success,
        "failure": failure,
        "total": total,
        "success_rate": success / total if total > 0 else 0.0
    }


if __name__ == "__main__":
    # Quick test
    print("Testing Brain module...")
    print()
    
    # Test retrieval
    result = retrieve_iam_steps("how do I grant a user access to a project")
    print(f"Retrieval result: {len(result['results'])} chunks found")
    for i, r in enumerate(result['results']):
        print(f"  {i+1}. [{r['similarity']:.3f}] {r['text'][:100]}...")
    print()
    
    # Test reward system
    update_step_reward("test-task", True)
    update_step_reward("test-task", False)
    stats = get_step_stats("test-task")
    print(f"Reward stats: {stats}")
