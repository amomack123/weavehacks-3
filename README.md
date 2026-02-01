# GCP Assistant Brain

A Python backend for the GCP Assistant featuring RAG retrieval with Redis Vector Search, RL reward tracking, and perceptual screen hashing.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| **Docker Desktop** | Latest |
| **Python** | 3.10+ |
| **Google API Key** | For Gemini embeddings |

---

## 🚀 Quick Start

### 1. Set up environment variables

Create a `.env` file in the project root:

```bash
GOOGLE_API_KEY=your-google-api-key-here
WANDB_API_KEY=your-wandb-api-key-here  # Optional, for Weave observability
REDIS_URL=redis://localhost:6379
```

### 2. Start the services

**Option A: Docker Compose (Recommended)**
```bash
docker-compose up --build
```

**Option B: Manual Redis Start**
```bash
docker run -d --name gcp-assistant-redis \
  -p 6379:6379 -p 8001:8001 \
  redis/redis-stack:latest
```

This will:
- Start Redis Stack with Vector Search enabled
- Expose Redis on **port 6379**
- Expose Redis Insight dashboard on **port 8001**

### 3. Install Python dependencies

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## ⚠️ CRITICAL: Data Ingestion

> **Pulling the code is NOT enough.**  
> You MUST run the ingestion script to populate the 116 IAM rules and build the search index.

```bash
python ingest_to_redis.py
```

**Expected output:**
```
🎉 Ingestion complete!
   Chunks: 116
   Index: iam_rules
```

**If you skip this step, the bot will be brain-dead** — it won't have any knowledge to retrieve.

---

## ✅ Verification

### Check the API
```bash
curl http://localhost:8000/health
```
Expected: `{"status": "healthy", "service": "gcp-assistant-brain"}`

### Check Redis Insight
1. Open http://localhost:8001
2. Go to **"Search and Query"** tab
3. Select **`iam_rules`** index
4. You should see **116 documents**

### Test RAG Endpoint
1. Open [http://localhost:8000/docs](http://localhost:8000/docs)
2. Try `POST /assist` with:
   ```json
   {
     "transcript": "how do I add a user to a project in GCP",
     "screenshot": ""
   }
   ```

### Test Reward Store
```bash
docker exec gcp-assistant-redis redis-cli KEYS "rewards:*"
```

---

## 📁 Project Structure

| File | Description |
|------|-------------|
| `api.py` | FastAPI server with `/assist`, `/reward`, and `/stats` endpoints |
| `brain.py` | RAG retrieval + RL reward store + screen hashing (phash) |
| `ingest_to_redis.py` | Script to ingest IAM knowledge into Redis |
| `iam_redis_manager.py` | Force sync and index management |
| `pipecat_bot.py` | Voice bot with Daily transport |
| `IAM_knowledge.txt` | Knowledge base for GCP IAM assistance |

---

## 🔧 Development (without Docker Compose)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start Redis Stack separately
docker run -d --name gcp-assistant-redis -p 6379:6379 -p 8001:8001 redis/redis-stack:latest

# Ingest knowledge base
python ingest_to_redis.py

# Run the API server
uvicorn api:app --reload --port 8000
```

---

## 📊 Observability

This project uses [Weave](https://wandb.ai/site/weave) for observability. All RAG retrievals and reward updates are tracked automatically.

To view traces, set your `WANDB_API_KEY` in `.env` and visit your Weights & Biases dashboard.

---

## 🛠 Troubleshooting

**Redis not starting?**
```bash
docker ps -a | grep redis
docker logs gcp-assistant-redis
```

**0 documents indexed?**
```bash
python iam_redis_manager.py  # Force sync the index
```

**Missing API key?**
Check your `.env` file has `GOOGLE_API_KEY` set.
