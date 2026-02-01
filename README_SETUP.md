# GCP Assistant Backend - Setup Guide

Get the Redis-powered RAG brain running in 5 minutes.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| **Docker Desktop** | Latest |
| **Python** | 3.10+ |

---

## Quick Start

### 1. Start Redis Stack

```bash
docker run -d --name gcp-assistant-redis \
  -p 6379:6379 -p 8001:8001 \
  redis/redis-stack:latest
```

This starts Redis with:
- **Port 6379**: Redis server
- **Port 8001**: Redis Insight UI (http://localhost:8001)

---

### 2. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Key packages: `redis`, `redisvl`, `imagehash`, `Pillow`, `numpy`

---

### 3. Set Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
GOOGLE_API_KEY=your_gemini_api_key
REDIS_URL=redis://localhost:6379
WANDB_API_KEY=your_wandb_key
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

If you skip this step, **the bot will be brain-dead** — it won't have any knowledge to retrieve.

---

## Verification

### Test the Brain Module

```bash
python brain.py
```

Uncomment the `if __name__ == "__main__":` block in `brain.py` first, then run to verify:
- Screen hashing (phash) works
- Reward store (HINCRBYFLOAT) works
- RAG retrieval finds chunks

### Check Redis Insight

1. Open http://localhost:8001
2. Go to **"Search and Query"** tab
3. Select **`iam_rules`** index
4. You should see **116 documents**

### Verify Reward Store

```bash
docker exec gcp-assistant-redis redis-cli KEYS "rewards:*"
```

---

## File Overview

| File | Purpose |
|------|---------|
| `brain.py` | RAG retrieval + RL reward store + screen hashing |
| `ingest_to_redis.py` | Populates the knowledge base |
| `iam_redis_manager.py` | Force sync and index management |
| `api.py` | FastAPI endpoints |
| `pipecat_bot.py` | Voice bot with Daily transport |

---

## Troubleshooting

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
