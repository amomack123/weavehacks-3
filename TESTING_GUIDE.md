# How to Test the Pipecat Voice Agent

Follow these steps to verify that the RAG context, Reward system, and Action coordination are working correctly.

## 1. Prerequisites
Ensure you have installed the requirements and created a `.env` file with at least dummy keys if you just want to test connection logic.

```bash
uv sync
```

## 2. Start the Agent (Brain)
Open a terminal and start the main Python process.

```bash
python main.py --debug
```

## 3. Run the Automated Test Suite
Open **another terminal** and run the test client. This script simulates a user speaking, the agent responding with coordinates, and Electron providing feedback.

```bash
python test_agent.py
```

### What to Look For (Success Criteria)

| Component | Check | Terminal Log to Verify |
| :--- | :--- | :--- |
| **Connection** | WebSocket handshake | `✓ WebSocket transport configured` |
| **STT Trigger** | User text received | `[USER]: Open the browser settings for me.` |
| **Reward Loop** | Feedback consumed | `Received feedback for action test_action_001` |
| **Episodic Memory**| Reward stored | `Episodic memory updated for test_action_001: Reward 1.0` |
| **RAG Injection** | Prompt updated | `System prompt updated with current RAG context` |

## 4. Manual RAG Testing
While the agent is running, you can manually trigger context updates to see how the LLM's "knowledge" changes in real-time.

```bash
python example_rag_usage.py
```

## 5. Structured Logs
Check the `logs/` directory. You should see two types of files:
- `conversation_*.jsonl`: Tracks what was said.
- `events_*.jsonl`: Tracks rewards, interruptions, and system errors.

```bash
# View the latest reward updates
tail -f logs/events_$(date +%Y-%m-%d).jsonl | grep reward
```

## 6. Verification Checklist
- [ ] Pipeline starts without service errors.
- [ ] WebSocket accepts connections from `test_agent.py`.
- [ ] Agent logs show "System prompt updated" when text is received.
- [ ] Reward Processor logs "Reward 1.0" when feedback is sent.
- [ ] JSONL logs show structured data for both user text and agent actions.
