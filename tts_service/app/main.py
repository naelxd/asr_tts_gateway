import math
import asyncio
import json
import os
import time
from typing import AsyncGenerator
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from TTS.api import TTS
from common.logger import logger

logger.info("Service started")


SAMPLE_RATE = int(os.getenv("TTS_SR", "16000"))
CHUNK_SAMPLES = int(os.getenv("TTS_CHUNK_SAMPLES", "640"))
MODEL_NAME = os.getenv("TTS_MODEL", "tts_models/en/ljspeech/tacotron2-DDC")

app = FastAPI(title="tts-service", version="0.1.0")
_tts = None


@app.middleware("http")
async def log_http_errors(request: Request, call_next):
    """Middleware для логирования HTTP ошибок 4xx/5xx"""
    start_time = time.time()

    response = await call_next(request)

    # Логируем ошибки 4xx и 5xx
    if response.status_code >= 400:
        process_time = time.time() - start_time
        logger.error(
            f"HTTP {response.status_code} error: {request.method} {request.url.path} "
            f"- {response.status_code} - {process_time:.3f}s - "
            f"client: {request.client.host if request.client else 'unknown'}"
        )

    return response


def get_tts():
    global _tts
    if _tts is None:
        try:
            _tts = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=False)
        except Exception:
            _tts = False
    return _tts if _tts is not False else None


async def generate_sine_fallback(text: str) -> AsyncGenerator[bytes, None]:
    duration = max(0.5, min(5.0, 0.07 * len(text)))
    total_samples = int(duration * SAMPLE_RATE)
    chunk_duration = CHUNK_SAMPLES / SAMPLE_RATE

    for i in range(0, total_samples, CHUNK_SAMPLES):
        chunk_size = min(CHUNK_SAMPLES, total_samples - i)
        chunk = bytearray()
        for j in range(chunk_size):
            t = (i + j) / SAMPLE_RATE
            val = 0.2 * math.sin(2 * math.pi * 220 * t)
            sample = int(val * 32767)
            chunk += sample.to_bytes(2, byteorder="little", signed=True)
        yield bytes(chunk)
        await asyncio.sleep(chunk_duration)


async def generate_tts(text: str) -> AsyncGenerator[bytes, None]:
    tts = get_tts()
    if not tts:
        async for chunk in generate_sine_fallback(text):
            yield chunk
        return

    try:
        wav = tts.tts(text=text)
        if not isinstance(wav, np.ndarray):
            wav = np.asarray(wav, dtype=np.float32)
        if len(wav) > SAMPLE_RATE:
            ratio = SAMPLE_RATE / 22050
            indices = np.linspace(0, len(wav) - 1, int(len(wav) * ratio)).astype(int)
            wav = wav[indices]

        pcm = (np.clip(wav, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        chunk_duration = CHUNK_SAMPLES / SAMPLE_RATE
        for i in range(0, len(pcm), CHUNK_SAMPLES * 2):
            chunk = pcm[i : i + CHUNK_SAMPLES * 2]
            if chunk:
                yield chunk
                await asyncio.sleep(chunk_duration)

    except Exception:
        async for chunk in generate_sine_fallback(text):
            yield chunk


@app.websocket("/ws/tts")
async def ws_tts(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    try:
        data = await websocket.receive_text()
        payload = json.loads(data)
        text = payload.get("text", "")

        if not text and payload.get("segments"):
            text = " ".join(seg.get("text", "") for seg in payload["segments"])
        if not text.strip():
            logger.warning("Empty text received")
            await websocket.send_text(json.dumps({"error": "text required"}))
            await websocket.close(code=1003)
            return

        logger.info(
            f"Generating audio for text: '{text[:50]}{'...' if len(text) > 50 else ''}'"
        )

        chunk_count = 0
        async for chunk in generate_tts(text):
            await websocket.send_bytes(chunk)
            chunk_count += 1

        logger.info(f"Audio generation completed, sent {chunk_count} chunks")
        await websocket.send_text(json.dumps({"type": "end"}))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except Exception:
            pass


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
