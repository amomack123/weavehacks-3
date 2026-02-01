# Python 3.10 slim base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install build-essential for AI libraries (numpy, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api.py brain.py ./
COPY IAM_knowledge.txt ./
COPY ingest_to_redis.py ./

# Expose port 8000
EXPOSE 8000

# Run uvicorn server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
