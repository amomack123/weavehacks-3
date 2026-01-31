# GCP Assistant Brain

A Python backend for the GCP Assistant featuring RAG retrieval with Redis Vector Search and RL reward tracking.

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose installed
- A Google API key (for Gemini embeddings)

### 1. Set up environment variables

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your-google-api-key-here
WANDB_API_KEY=your-wandb-api-key-here  # Optional, for Weave observability
```

### 2. Start the services

```bash
docker-compose up --build
```

This single command will:
- Build the brain-api container with all dependencies
- Start Redis Stack with Vector Search enabled
- Expose the FastAPI server on **port 8000**
- Expose Redis Insight dashboard on **port 8001**

### 3. Verify everything is working

Open the interactive API docs:
- **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Redis Insight**: [http://localhost:8001](http://localhost:8001)

#### Test the RAG endpoint:
1. Navigate to [http://localhost:8000/docs](http://localhost:8000/docs)
2. Click on the `POST /assist` endpoint
3. Click "Try it out"
4. Enter a test request:
   ```json
   {
     "transcript": "how do I add a user to a project in GCP",
     "screenshot": ""
   }
   ```
5. Click "Execute" and verify you receive navigation instructions

#### Health Check:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "gcp-assistant-brain"}
```

## 📁 Project Structure

| File | Description |
|------|-------------|
| `api.py` | FastAPI server with `/assist`, `/reward`, and `/stats` endpoints |
| `brain.py` | RAG retrieval and RL reward logic |
| `ingest_to_redis.py` | Script to ingest IAM knowledge into Redis |
| `IAM_knowledge.txt` | Knowledge base for GCP IAM assistance |

## 🔧 Development (without Docker)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis Stack separately
docker run -d --name redis-stack -p 6379:6379 -p 8001:8001 redis/redis-stack:latest

# Run the API server
uvicorn api:app --reload --port 8000
```

## 📊 Observability

This project uses [Weave](https://wandb.ai/site/weave) for observability. All RAG retrievals and reward updates are tracked automatically.

To view traces, set your `WANDB_API_KEY` in `.env` and visit your Weights & Biases dashboard.
