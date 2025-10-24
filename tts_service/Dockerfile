FROM python:3.10-slim

WORKDIR /app

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

RUN pip install --upgrade pip setuptools wheel
COPY tts_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tts_service/app/ ./app/
COPY common/ ./common/

RUN mkdir -p /opt/models /var/log/app

EXPOSE 8082

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8082/healthz || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8082"]
