FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY create_group_description.py .

# Set Python path to include src directory
ENV PYTHONPATH=/app

# Expose health check port
EXPOSE 8000

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health/simple || exit 1

# Run the application with smart entry point that selects mode based on RUN_MODE
# RUN_MODE=service: Uses persistent service mode (prevents restart loops)
# RUN_MODE=oneshot: Uses traditional oneshot mode (default for backward compatibility)
CMD ["python", "-m", "src.main"]
