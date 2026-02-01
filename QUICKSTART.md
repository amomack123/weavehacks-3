# Quick Start Guide

## 30-Second Setup

```bash
# 1. Install dependencies
uv sync

# 2. Configure API keys
cp .env.example .env
# Edit .env and add your DEEPGRAM_API_KEY and OPENAI_API_KEY

# 3. Run
python main.py
```

## What You Get

```
weavehacks-3/
├── main.py              ← Run this
└── app/
    ├── config.py        ← All settings
    ├── rag.py           ← update_rag_context() here
    ├── services.py      ← STT/LLM/TTS setup
    ├── pipeline.py      ← Pipeline assembly
    ├── handlers.py      ← Event handlers
    ├── logging_utils.py ← Conversation logs
    └── vision_hooks.py  ← Templates only
```

## Key Concepts

### 1. RAG Context Injection

```python
# From another script or REPL:
from app.rag import update_rag_context

update_rag_context("Today's context: ...")
# Next user query uses this context automatically
```

### 2. Where Things Happen

**User speaks** → STT (Deepgram) → **`on_text_message`** handler:
- Injects current RAG context into system prompt
- Calls `llm_service.set_system_prompt()` (no service recreation!)

**LLM responds** → TTS (Cartesia/Silero) → **User hears response**

**`on_app_message`** handler:
- Logs conversation turn to `logs/conversation_*.jsonl`

### 3. No Manual Chat History

✅ Pipecat manages conversation history automatically  
❌ Don't implement your own message list

### 4. Efficient RAG Updates

✅ Per-request prompt injection via `set_system_prompt()`  
❌ Don't recreate `OpenAIService` on context changes

## Common Tasks

### Change LLM Model
```bash
# Edit .env:
LLM_MODEL=gpt-4o  # or gpt-4-turbo, gpt-3.5-turbo
```

### Debug Mode
```bash
python main.py --debug
```

### View Logs
```bash
tail -f logs/conversation_$(date +%Y-%m-%d).jsonl
```

### Test RAG Context
```bash
python example_rag_usage.py
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `DEEPGRAM_API_KEY not set` | Add to `.env` file |
| Import errors | Run `uv sync` or `pip install -e .` |
| No audio | Check TTS service logs, verify CARTESIA_API_KEY |
| Context not used | Check logs for "System prompt updated" |

## Next Steps

1. **Add vector DB**: Auto-retrieve context from ChromaDB/Pinecone
2. **Implement vision**: Fill in `app/vision_hooks.py` templates
3. **Deploy**: Add authentication, rate limiting, monitoring

## Architecture Decisions

**Why modules?**
- Separation of concerns
- Easy to test each component
- Clear dependencies

**Why per-request prompts?**
- Efficient (no service recreation)
- Clean (Pipecat supports it)
- Fast context updates

**Why global RAG context?**
- Simple external API
- Thread-safe
- Can be called from anywhere

---

**Read the full [README.md](./README.md) for details**
