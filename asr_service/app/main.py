from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import numpy as np
from typing import List
from faster_whisper import WhisperModel
from common.logger import logger

logger.info("Service started")


DEFAULT_SR = int(os.getenv("ASR_SR", "16000"))
MAX_SECONDS = float(os.getenv("ASR_MAX_SECONDS", "15"))
MODEL_NAME = os.getenv("ASR_MODEL", "tiny.en")

app = FastAPI(title="asr-service", version="0.1.0")
_model = None


def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {MODEL_NAME}")
        try:
            _model = WhisperModel(MODEL_NAME, device="cpu", compute_type="int8")
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    return _model


def pcm_s16le_bytes_to_float32_mono(
    data: bytes, channels: int, sample_rate: int
) -> np.ndarray:
    if channels != 1:
        raise HTTPException(status_code=400, detail="Only mono (ch=1) supported")
    if sample_rate <= 0:
        raise HTTPException(status_code=400, detail="Invalid sample rate")
    arr = np.frombuffer(data, dtype="<i2").astype(np.float32)
    if arr.size == 0:
        return np.zeros(0, dtype=np.float32)
    arr /= 32768.0
    return arr


@app.post("/api/stt/bytes")
async def stt_bytes(
    request: Request, sr: int = DEFAULT_SR, ch: int = 1, lang: str = "en"
):
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty body")

    audio = pcm_s16le_bytes_to_float32_mono(body, channels=ch, sample_rate=sr)
    max_samples = int(MAX_SECONDS * sr)
    if audio.shape[0] > max_samples:
        raise HTTPException(
            status_code=400, detail=f"Audio too long (> {MAX_SECONDS}s)"
        )

    # Логируем информацию о входящем аудио
    duration = len(audio) / sr
    logger.info(f"Processing audio: {len(body)} bytes, {duration:.2f}s, lang={lang}")

    try:
        model = get_model()
        segments_iter, _ = model.transcribe(audio, language=lang, vad_filter=False)

        text_parts: List[str] = []
        segments_out: List[dict] = []
        segment_count = 0

        for seg in segments_iter:
            text_parts.append(seg.text)
            segments_out.append(
                {
                    "start_ms": int(seg.start * 1000),
                    "end_ms": int(seg.end * 1000),
                    "text": seg.text.strip(),
                }
            )
            segment_count += 1

        result_text = " ".join(t.strip() for t in text_parts).strip()

        # Логируем результат транскрипции
        if result_text:
            logger.info(
                f"Transcription completed: '{result_text[:50]}"
                f"{'...' if len(result_text) > 50 else ''}' "
                f"({segment_count} segments)"
            )
        else:
            logger.warning("No speech detected in audio")

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Transcription error: {str(e)}"
        ) from e

    return JSONResponse(
        {
            "text": result_text,
            "segments": segments_out,
        }
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
