FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

RUN pip install uv

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    git \
    sqlite3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create finance agent directory
RUN mkdir -p /app/finance

# Copy common OAuth utilities
COPY common/ /app/common/

# Copy application code
COPY agents/finance/__main__.py agents/finance/finance_agent.py agents/finance/globals.py agents/finance/pyproject.toml agents/finance/uv.lock agents/finance/finance_agent_taskmanager.py  /app/finance/

RUN uv sync  --directory finance --locked

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8888 \
    BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0 \
    AWS_REGION=us-west-2 \
    PYTHONPATH=/app:/app/finance

# Expose the port the app runs on
EXPOSE 8888

# Command to run the application
CMD ["uv", "run", "--directory",  "finance","__main__.py", "--host", "0.0.0.0", "--port", "8888"]

