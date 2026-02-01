"""
Ingest IAM_knowledge.txt into Redis for RAG with Weave observability.

Usage:
    python ingest_to_redis.py

Environment Variables:
    GOOGLE_API_KEY: Gemini API key (get free at https://aistudio.google.com/)
    REDIS_URL: Redis connection URL (default: redis://localhost:6379)
    WANDB_API_KEY: Weights & Biases API key for Weave
"""

import os
from pathlib import Path

import numpy as np
import weave
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from redisvl.index import SearchIndex
from redisvl.schema import IndexSchema

# Load environment variables
load_dotenv()

# Configuration
KNOWLEDGE_FILE = Path(__file__).parent / "IAM_knowledge.txt"
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
INDEX_NAME = "iam_knowledge"


@weave.op()
def load_and_split_text(file_path: Path, chunk_size: int = 600, chunk_overlap: int = 100) -> list[str]:
    """Load text file and split into chunks."""
    print(f"📄 Loading {file_path}...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = splitter.split_text(text)
    print(f"✂️  Split into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap})")
    
    return chunks


@weave.op()
def create_embeddings_model():
    """Create Gemini embeddings model."""
    print("🔧 Initializing Gemini embeddings (models/embedding-001)...")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    
    return embeddings


@weave.op()
def embed_chunks(chunks: list[str], embeddings_model) -> list[list[float]]:
    """Embed all chunks using the embeddings model."""
    print(f"🔢 Embedding {len(chunks)} chunks...")
    
    embeddings = embeddings_model.embed_documents(chunks)
    
    print(f"✅ Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")
    return embeddings


@weave.op()
def store_in_redis(chunks: list[str], embeddings: list[list[float]], redis_url: str, index_name: str):
    """Store embedded chunks in Redis vector store using redisvl."""
    print(f"📦 Storing {len(chunks)} chunks in Redis index '{index_name}'...")
    
    # Get embedding dimension
    dim = len(embeddings[0])
    
    # Define schema for the index
    schema = IndexSchema.from_dict({
        "index": {
            "name": index_name,
            "prefix": f"{index_name}:",
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
                    "dims": dim,
                    "distance_metric": "cosine",
                    "datatype": "float32"
                }
            }
        ]
    })
    
    # Create index
    index = SearchIndex(schema, redis_url=redis_url)
    
    # Try to delete existing index, create new one
    try:
        index.delete(drop=True)
    except:
        pass
    
    index.create(overwrite=True)
    
    # Prepare data for loading - convert embeddings to bytes
    data = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        # Convert embedding to numpy array and then to bytes for Redis
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
        data.append({
            "text": chunk,
            "chunk_id": f"chunk_{i}",
            "embedding": embedding_bytes
        })
    
    # Load data into Redis
    index.load(data)
    
    print(f"✅ Successfully stored {len(chunks)} chunks in Redis!")
    return index


@weave.op()
def ingest_iam_knowledge() -> dict:
    """
    Main ingestion pipeline: Load → Split → Embed → Store in Redis.
    
    This is the top-level operation visible in the W&B Weave dashboard.
    """
    print("🚀 Starting IAM Knowledge ingestion pipeline...")
    print(f"   Redis URL: {REDIS_URL}")
    print(f"   Index Name: {INDEX_NAME}")
    print()
    
    # Step 1: Load and split text
    chunks = load_and_split_text(KNOWLEDGE_FILE, chunk_size=600, chunk_overlap=100)
    
    # Step 2: Create embeddings model
    embeddings_model = create_embeddings_model()
    
    # Step 3: Embed all chunks
    embeddings = embed_chunks(chunks, embeddings_model)
    
    # Step 4: Store in Redis
    index = store_in_redis(chunks, embeddings, REDIS_URL, INDEX_NAME)
    
    result = {
        "status": "success",
        "chunks_created": len(chunks),
        "index_name": INDEX_NAME,
        "redis_url": REDIS_URL
    }
    
    print()
    print("=" * 50)
    print("🎉 Ingestion complete!")
    print(f"   Chunks: {len(chunks)}")
    print(f"   Index: {INDEX_NAME}")
    print("=" * 50)
    
    return result


if __name__ == "__main__":
    # Initialize Weave for W&B observability
    weave.init("gcp-assistant-rag") 
    
    # Run the ingestion pipeline
    result = ingest_iam_knowledge()
    
    print()
    print("📊 View the data flow in your W&B Weave dashboard:")
    print("   https://wandb.ai/home → Select 'gcp-assistant-rag' project → Weave tab")
