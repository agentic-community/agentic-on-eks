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

COPY agents/admin/pyproject.toml agents/admin/uv.lock ./
COPY agents/admin/*.py ./
COPY common/ ./common/



RUN uv sync

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