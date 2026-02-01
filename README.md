# Pipecat AI Voice Agent

Production-ready conversational voice AI agent with **modular architecture**.

## 🏗️ Architecture

```
weavehacks-3/
├── main.py                 # Thin entrypoint
├── pyproject.toml          # Dependencies
├── .env                    # API keys (create from .env.example)
├── .env.example            # Environment template
├── logs/                   # Conversation logs (auto-created)
└── app/
    ├── __init__.py
    ├── config.py           # Environment variables & constants
    ├── services.py         # STT/LLM/TTS service factories
    ├── rag.py              # Dynamic RAG context management
    ├── pipeline.py         # Pipeline assembly
    ├── handlers.py         # Event handlers (@pipeline.on)
    ├── logging_utils.py    # JSONL conversation logging
    └── vision_hooks.py     # Qwen2+SAM templates (not implemented)
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env and add your API keys
# Required: DEEPGRAM_API_KEY, OPENAI_API_KEY
# Optional: CARTESIA_API_KEY (falls back to Silero)
```

### 3. Run

```bash
python main.py

# With debug logging
python main.py --debug
```

## 📖 Key Features

### ✅ Modular Architecture
Each concern is separated:
- **config.py**: All configuration in one place
- **services.py**: Service initialization logic
- **rag.py**: RAG context management (thread-safe)
- **pipeline.py**: Pipeline assembly
- **handlers.py**: Event handling
- **logging_utils.py**: Structured logging

### ✅ Dynamic RAG Context Injection

**Per-request injection** - context updates without recreating services:

```python
from app.rag import update_rag_context

# Update context externally when topic changes
update_rag_context("""
Google Kubernetes Engine (GKE):
- Managed Kubernetes service
- Auto-scaling, node pools
- Integration with Cloud services
""")

# Next user query will use this context automatically
```

**How it works:**
1. Global `current_rag_context` variable in `rag.py`
2. `handlers.py` calls `build_system_prompt()` before each LLM request
3. System prompt updated via `llm_service.set_system_prompt()` 
4. **No service recreation** - just prompt update

### ✅ Conversation History
Pipecat manages chat history automatically - we don't need to implement it!

### ✅ Event Handlers
All event handlers in `app/handlers.py`:
- `on_text_message`: STT transcription → inject RAG context
- `on_app_message`: LLM response → log conversation
- `on_interruption`: User interrupts agent
- `on_error`: Pipeline errors

### ✅ Structured Logging
JSONL logs in `./logs/`:
- `conversation_YYYY-MM-DD.jsonl`: User/agent turns
- `events_YYYY-MM-DD.jsonl`: System events

Example log entry:
```json
{
  "session_id": "20260131_153000",
  "timestamp": "2026-01-31T23:30:00.123Z",
  "user": "What is GKE?",
  "agent": "GKE is Google Kubernetes Engine...",
  "rag_context_length": 245,
  "metadata": {"rag_context_preview": "Google Kubernetes..."}
}
```

## 🔧 Configuration

Edit `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPGRAM_API_KEY` | *required* | Deepgram STT API key |
| `OPENAI_API_KEY` | *required* | OpenAI LLM API key |
| `CARTESIA_API_KEY` | *optional* | Cartesia TTS (or use Silero) |
| `WEBSOCKET_URL` | `ws://localhost:8000/ws` | WebSocket endpoint |
| `STT_MODEL` | `nova-2` | Deepgram model |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model |
| `LLM_TEMPERATURE` | `0.7` | LLM creativity (0-2) |
| `LLM_MAX_TOKENS` | `150` | Max response length |

## 🧪 Testing

### Test Pipeline
```bash
python main.py
# Expected: "✓ Pipeline started successfully"
```

### Test RAG Context
```python
# In another terminal, Python REPL:
from app.rag import update_rag_context

update_rag_context("Test context about Kubernetes")
# Speak to agent: "What can you tell me?"
# Agent should reference the context
```

### Test Logs
```bash
# Check logs directory
ls -la logs/

# View conversation log
tail -f logs/conversation_$(date +%Y-%m-%d).jsonl
```

## 📁 Module Details

### `app/config.py`
- Loads `.env` variables
- Defines all constants
- `validate_config()` checks required keys
- System prompt template

### `app/services.py`
Factory functions:
- `create_stt_service()`: Deepgram with VAD
- `create_llm_service()`: OpenAI with conversation history
- `create_tts_service()`: Cartesia or Silero fallback

### `app/rag.py`
RAG context management:
- `update_rag_context(new_context)`: Thread-safe update
- `get_rag_context()`: Retrieve current context
- `build_system_prompt(template)`: Inject context into prompt

### `app/pipeline.py`
- `create_pipeline()`: Assembles full pipeline
- Wires: WebSocket → STT → LLM → TTS → WebSocket
- Registers event handlers

### `app/handlers.py`
Event handlers:
- **Per-request RAG injection**: `on_text_message` updates system prompt
- Conversation turn logging
- Interruption handling
- Error tracking

### `app/logging_utils.py`
- `ConversationLogger` class
- `log_turn()`: Log user/agent exchanges
- `log_event()`: Log system events
- JSONL format for easy parsing

### `app/vision_hooks.py` (Template Only)
Templates for future vision integration:
- `capture_screen_context()`: Qwen2-VL screen description
- `detect_screen_objects()`: SAM object detection
- `vision_rag_update_loop()`: Auto-refresh context

**To implement:**
1. Install vision dependencies: `pip install -e ".[vision]"`
2. Implement template functions
3. Enable loop in `main.py` or `pipeline.py`

## 🎯 Design Decisions

### Why per-request prompt injection?
✅ **Efficient**: No service recreation overhead  
✅ **Fast**: Just updates system prompt string  
✅ **Clean**: Pipecat supports `set_system_prompt()`  

❌ **Not**: Recreating `OpenAIService` on every context change

### Why no custom chat history?
✅ Pipecat manages conversation history internally  
✅ Multi-turn conversations work automatically  
✅ No need to track message list ourselves  

### Why global RAG context?
✅ Simple external API: `update_rag_context()`  
✅ Thread-safe with lock  
✅ Can be called from anywhere (vector DB, topic detector, etc.)  

## 🚀 Next Steps

1. **Add vector database**: Auto-retrieve RAG context
2. **Implement vision hooks**: Screen context extraction
3. **Add WebSocket server**: Currently assumes external server
4. **Multi-user support**: Session management
5. **Metrics**: Prometheus/Grafana monitoring

## 📚 Resources

- [Pipecat Docs](https://docs.pipecat.ai/)
- [Implementation Plan](/.gemini/antigravity/brain/*/pipecat_implementation_plan.md)

---

**Built with ❤️ using Pipecat AI**
