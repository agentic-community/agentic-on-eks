# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Install dependencies directly
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install \
        "a2a>=0.44" \
        "a2a-sdk>=0.2.5" \
        "a2a-server>=0.1.0" \
        "boto3>=1.28.64" \
        "click>=8.1.8" \
        "fastapi>=0.104.1" \
        "httpx>=0.25.0" \
        "langchain>=0.0.335" \
        "langchain-aws>=0.2.23" \
        "pydantic>=2.7.2,<3.0.0" \
        "python-dotenv>=1.0.0" \
        "uvicorn>=0.23.2"

# Copy application files
COPY *.py ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash agent && \
    chown -R agent:agent /app
USER agent

# Expose port
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_REGION=us-west-2
ENV PATH="/app/.venv/bin:$PATH"

# Run the application
CMD [".venv/bin/python", "__main__.py", "--host", "0.0.0.0", "--port", "8080"]