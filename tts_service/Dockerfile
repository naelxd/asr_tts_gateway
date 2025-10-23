FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    ffmpeg \
    libsndfile1 \
    python3-dev \
    cmake \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel
# Copy requirements and install Python dependencies
COPY tts_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY tts_service/app/ ./app/
COPY common/ ./common/

# Create directories for models and logs
RUN mkdir -p /opt/models /var/log/app

# Expose port
EXPOSE 8082

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8082/healthz || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
