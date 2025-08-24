FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

RUN pip install uv

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    python3-dev \
    sqlite3 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache


# mem0ai is now installed from requirements.txt

# Create HR agent directory
RUN mkdir -p /app/hr

# Copy common OAuth utilities
COPY common/ /app/common/

# Copy MCP server files
COPY agents/hr/mcp_server/ /app/hr/mcp_server/

# Copy application code
COPY agents/hr/__main__.py agents/hr/hr_agent.py agents/hr/hr_agent_taskmanager.py agents/hr/utils.py agents/hr/config.yaml agents/hr/pyproject.toml agents/hr/uv.lock /app/hr/

RUN uv sync  --directory hr --locked




# Create a directory for the SQLite database with proper permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    MCP_SERVER_PATH=/app/hr/mcp_server \
    PUBLIC_HOLIDAY_SERVER_FNAME=nager_mcp_server.py \
    CONFIG_PATH=/app/hr/config.yaml \
    SQLITE_DB_PATH=/app/data/hr_database.sqlite \
    PYTHONPATH=/app:/app/hr

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uv", "run", "--directory",  "hr","__main__.py", "--host", "0.0.0.0", "--port", "8000"]
