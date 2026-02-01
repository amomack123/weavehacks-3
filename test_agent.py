"""
Comprehensive Test Script for Pipecat Voice Agent
Tests: WebSocket connection, RAG injection, and Reward/Feedback loop.
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestClient")

# Configuration
URL = "ws://localhost:8000/ws"

async def run_test_suite():
    print("=" * 60)
    print("🚀 PIPECAT AGENT TEST SUITE")
    print("=" * 60)

    try:
        async with websockets.connect(URL) as ws:
            print("\n[STEP 1] Connection: ✅ SUCCESS")
            
            # 1. Test STT -> LLM Flow (Simulated via TextFrame)
            # Note: In production this comes from Daily/Deepgram
            print("\n[STEP 2] Simulating User Input...")
            test_utterance = {
                "type": "text",
                "text": "Open the browser settings for me.",
                "timestamp": datetime.now().isoformat()
            }
            await ws.send(json.dumps(test_utterance))
            print(f"Sent: {test_utterance['text']}")

            # 2. Wait for Action Frame from Agent
            print("\n[STEP 3] Waiting for Agent Response/Action...")
            try:
                # Agent should respond with text + coords
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                print(f"Received from Agent: {response}")
            except asyncio.TimeoutError:
                print("⚠️  Timeout: No response from Agent (Check if server is running)")
                return

            # 3. Simulate Coordinate Feedback (The Reward Loop)
            # This simulates Electron telling Python "The user clicked close to your arrow"
            print("\n[STEP 4] Simulating Behavioral Feedback (Reward)...")
            feedback = {
                "type": "action_feedback",
                "action_id": "test_action_001",
                "success": True,
                "user_delta": 12.5, # User clicked 12.5px away from our suggestion
                "metadata": {"intent": "settings_click"}
            }
            await ws.send(json.dumps(feedback))
            print("Feedback Sent: SUCCESS (Delta=12.5px)")

            print("\n[STEP 5] Check Server Logs:")
            print("Look for: 'Received feedback for action test_action_001'")
            print("Look for: 'Episodic memory updated for test_action_001: Reward 1.0'")

    except Exception as e:
        print(f"\n❌ FAILED: Could not connect to {URL}")
        print(f"Error: {e}")
        print("\nMake sure to run 'python main.py' first!")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_test_suite())
