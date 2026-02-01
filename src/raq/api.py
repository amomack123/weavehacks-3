"""
FastAPI server for GCP Assistant Electron Bridge.

This provides an HTTP API that the Electron app can call to:
1. Get navigation instructions based on voice transcript
2. Report success/failure for RL reward tracking

Usage:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST /assist - Get navigation instructions from voice transcript
    POST /reward - Report success/failure for a task step
    GET /health  - Health check endpoint
"""

import os
from typing import Optional

import weave
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from brain import retrieve_iam_steps, update_step_reward, get_step_stats

# Load environment variables
load_dotenv()

# Initialize Weave for observability
# weave.init("gcp-assistant-rag")

# Create FastAPI app
app = FastAPI(
    title="GCP Assistant Brain API",
    description="Python Brain backend for GCP Assistant with RAG retrieval and RL rewards",
    version="1.0.0"
)

# Configure CORS for Electron app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Electron
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class AssistRequest(BaseModel):
    """Request body for /assist endpoint."""
    screenshot: str = ""  # Base64 encoded screenshot (optional for now)
    transcript: str  # Voice transcript from user


class Coordinates(BaseModel):
    """UI coordinates for overlay."""
    x: Optional[float] = None
    y: Optional[float] = None


class InstructionStep(BaseModel):
    """A single navigation instruction step."""
    step: int
    text: str
    coordinates: Coordinates


class AssistResponse(BaseModel):
    """Response body for /assist endpoint."""
    instructions: list[InstructionStep]
    source_chunks: list[str]


class RewardRequest(BaseModel):
    """Request body for /reward endpoint."""
    task_id: str
    success: bool


class RewardResponse(BaseModel):
    """Response body for /reward endpoint."""
    task_id: str
    success_count: int
    failure_count: int
    success_rate: float


class StatsResponse(BaseModel):
    """Response body for /stats endpoint."""
    task_id: str
    success: int
    failure: int
    total: int
    success_rate: float


# Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gcp-assistant-brain"}


@app.post("/assist", response_model=AssistResponse)
@weave.op()
async def assist(request: AssistRequest):
    """
    Get navigation instructions based on voice transcript.
    
    The Electron app sends a screenshot and voice transcript,
    and receives step-by-step navigation instructions.
    """
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript cannot be empty")
    
    # Retrieve relevant IAM steps from Redis
    retrieval_result = retrieve_iam_steps(request.transcript, top_k=2)
    
    if not retrieval_result["results"]:
        raise HTTPException(status_code=404, detail="No relevant IAM steps found")
    
    # Convert retrieved chunks into instruction steps
    instructions = []
    source_chunks = []
    
    for i, chunk in enumerate(retrieval_result["results"]):
        # Extract text and create instruction step
        text = chunk["text"]
        source_chunks.append(text)
        
        # Parse text into actionable steps
        # For now, we return the raw text as instructions
        # Future: Use Gemini to extract specific action steps
        instructions.append(InstructionStep(
            step=i + 1,
            text=text[:500],  # Truncate long text
            coordinates=Coordinates()  # Null coordinates for now
        ))
    
    return AssistResponse(
        instructions=instructions,
        source_chunks=source_chunks
    )


@app.post("/reward", response_model=RewardResponse)
@weave.op()
async def report_reward(request: RewardRequest):
    """
    Report success/failure for RL reward tracking.
    
    The Electron app calls this after the user completes or fails a step.
    """
    result = update_step_reward(request.task_id, request.success)
    
    return RewardResponse(
        task_id=result["task_id"],
        success_count=result["success_count"],
        failure_count=result["failure_count"],
        success_rate=result["success_rate"]
    )


@app.get("/stats/{task_id}", response_model=StatsResponse)
@weave.op()
async def get_stats(task_id: str):
    """
    Get current reward statistics for a task.
    """
    stats = get_step_stats(task_id)
    
    return StatsResponse(
        task_id=stats["task_id"],
        success=stats["success"],
        failure=stats["failure"],
        total=stats["total"],
        success_rate=stats["success_rate"]
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
