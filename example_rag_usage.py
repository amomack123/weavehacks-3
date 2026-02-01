"""
Example: How to use RAG context injection

This script demonstrates updating RAG context externally
while the voice agent is running.
"""

import time
from app.rag import update_rag_context, get_rag_context

# Example 1: Update context for GKE questions
print("=" * 60)
print("Example 1: GKE Context")
print("=" * 60)

gke_context = """
Google Kubernetes Engine (GKE) Information:

- GKE is a managed Kubernetes service on Google Cloud Platform
- Key features:
  * Auto-scaling of nodes and pods
  * Auto-repair: automatic node health monitoring
  * Auto-upgrade: managed Kubernetes version updates
  * Node pools: groups of nodes with same configuration
  * Workload Identity: secure service account mapping
  
- Integration:
  * Cloud Monitoring for metrics
  * Cloud Logging for centralized logs
  * Cloud Build for CI/CD
  * Artifact Registry for container images

- Pricing:
  * Cluster management: $0.10/hour per cluster
  * Node compute: standard GCE pricing
  * Free tier: 1 cluster (zonal)
"""

update_rag_context(gke_context)
print(f"✓ Updated RAG context ({len(gke_context)} chars)")
print("\nNow ask the agent: 'What is GKE?' or 'Tell me about GKE pricing'")
print("The agent will use this context in its response.\n")

time.sleep(2)

# Example 2: Switch to Vertex AI context
print("=" * 60)
print("Example 2: Vertex AI Context")
print("=" * 60)

vertex_context = """
Vertex AI Information:

- Unified MLOps platform on Google Cloud
- Components:
  * AutoML: No-code ML model training
  * Custom Training: Bring your own code
  * Model Registry: Centralized model management
  * Endpoints: Managed model deployment
  * Pipelines: Orchestrated ML workflows
  * Feature Store: Centralized feature management
  
- Key capabilities:
  * Pre-built algorithms for common tasks
  * Support for TensorFlow, PyTorch, scikit-learn
  * Distributed training with GPUs/TPUs
  * A/B testing for model versions
  * Monitoring and explainability
  
- Use cases:
  * Image classification and object detection
  * Natural language processing
  * Tabular data prediction
  * Time series forecasting
"""

update_rag_context(vertex_context)
print(f"✓ Updated RAG context ({len(vertex_context)} chars)")
print("\nNow ask the agent: 'What is Vertex AI?' or 'How do I deploy models?'")
print("The agent will now use this new context.\n")

time.sleep(2)

# Example 3: Clear context
print("=" * 60)
print("Example 3: Clear Context")
print("=" * 60)

update_rag_context("")
print("✓ Cleared RAG context")
print("\nNow the agent will rely on general knowledge only.\n")

# Show current context
current = get_rag_context()
print(f"Current RAG context length: {len(current)} chars")
if current:
    print(f"Preview: {current[:100]}...")
else:
    print("Context is empty")

print("\n" + "=" * 60)
print("Integration Examples")
print("=" * 60)

print("""
# Integration with vector database:
from app.rag import update_rag_context
import chromadb

# Query vector DB for relevant context
def update_context_from_query(user_query: str):
    # Get relevant documents from vector DB
    results = collection.query(
        query_texts=[user_query],
        n_results=3
    )
    
    # Combine into context
    context = "\\n\\n".join(results['documents'][0])
    
    # Update RAG context
    update_rag_context(context)

# Integration with topic detector:
def on_topic_change(new_topic: str):
    # Load context for new topic
    context = load_topic_context(new_topic)
    update_rag_context(context)

# Integration with document loader:
def on_document_loaded(doc_path: str):
    # Extract text from document
    text = extract_text(doc_path)
    
    # Summarize if too long
    if len(text) > 2000:
        text = summarize(text, max_length=2000)
    
    update_rag_context(text)
""")
