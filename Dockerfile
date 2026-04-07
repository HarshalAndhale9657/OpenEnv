# IncidentForge — Production Incident Response RL Environment
# Dockerfile at project root for OpenEnv / HF Spaces deployment
FROM python:3.11-slim

# Metadata
LABEL maintainer="IncidentForge Team"
LABEL description="Production Incident Response RL Environment for OpenEnv"

# Set working directory
WORKDIR /app

# Copy requirements first for layer caching
COPY incident_forge/server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# Copy the entire project source
COPY . /app/

# Environment variables
ENV ENABLE_WEB_INTERFACE=true
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV WORKERS=1
ENV MAX_CONCURRENT_ENVS=100

# Health check — verifies the server is responsive using Python
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Expose the server port
EXPOSE 8000

# Launch via uvicorn with configurable workers
CMD uvicorn incident_forge.server.app:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers ${WORKERS}
