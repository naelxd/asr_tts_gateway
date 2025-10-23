from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import requests
import websockets
import os
from typing import AsyncGenerator
from common.logger import logger

logger.info("Service started")


TTS_WS_URL = os.getenv("TTS_WS_URL", "ws://localhost:8082/ws/tts")
ASR_URL = os.getenv("ASR_URL", "http://localhost:8081/api/stt/bytes")

app = FastAPI(title="gateway", version="0.1.0")


async def safe_send_json(ws: WebSocket, data: dict):
    """Отправка JSON через WebSocket с безопасной обработкой исключений."""
    try:
        await ws.send_text(json.dumps(data))
    except Exception:
        pass


async def forward_to_tts(
    client_ws: WebSocket, tts_ws: websockets.WebSocketClientProtocol
):
    """Пересылает сообщения от клиента к TTS."""
    try:
        while True:
            data = await client_ws.receive_text()
            try:
                payload = json.loads(data)
                if "segments" in payload and "text" not in payload:
                    segments = payload.get("segments", [])
                    text = " ".join(
                        seg.get("text", "") for seg in segments if seg.get("text")
                    )
                    await tts_ws.send(json.dumps({"text": text}))
                else:
                    await tts_ws.send(data)
            except json.JSONDecodeError:
                await tts_ws.send(data)
    except WebSocketDisconnect:
        return
    except Exception:
        return


async def forward_to_client(
    client_ws: WebSocket, tts_ws: websockets.WebSocketClientProtocol
):
    """Пересылает сообщения от TTS к клиенту."""
    try:
        async for message in tts_ws:
            if isinstance(message, bytes):
                await client_ws.send_bytes(message)
            else:
                try:
                    data = json.loads(message)
                    if data.get("type") == "end":
                        await client_ws.send_text(json.dumps({"type": "end"}))
                        break
                except Exception:
                    pass
    except WebSocketDisconnect:
        return
    except Exception as e:
        logger.error(f"Error in forward_to_client: {e}")
        return


# ---------------------
# Основная функция прокси
# ---------------------


async def proxy_tts_ws(client_ws: WebSocket, tts_ws_url: str):
    """Основной прокси для WebSocket TTS."""
    try:
        async with websockets.connect(tts_ws_url) as tts_ws:
            logger.info("Connected to TTS service")

            # 1️⃣ Сразу принимаем первый JSON с текстом
            try:
                first_msg = await client_ws.receive_text()
                await tts_ws.send(first_msg)
            except Exception as e:
                logger.error(f"Failed to read initial message: {e}")
                await safe_send_json(client_ws, {"error": str(e)})
                return

            # 2️⃣ Запускаем пересылку в обе стороны
            try:
                await asyncio.gather(
                    forward_to_tts(client_ws, tts_ws),
                    forward_to_client(client_ws, tts_ws),
                    return_exceptions=True,
                )
            except Exception as e:
                logger.error(f"Error in proxy gather: {e}")
                await safe_send_json(client_ws, {"error": str(e)})
            finally:
                # Закрываем соединение с клиентом
                try:
                    await client_ws.close()
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"Proxy error: {e}")
        await safe_send_json(client_ws, {"error": str(e)})
        try:
            await client_ws.close(code=1011)
        except Exception:
            pass


async def echo_bytes_stream(pcm_data: bytes) -> AsyncGenerator[bytes, None]:
    try:
        asr_resp = requests.post(
            f"{ASR_URL}?sr=16000&ch=1&lang=en",
            data=pcm_data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=30,
        )
        asr_resp.raise_for_status()
        text = asr_resp.json().get("text", "").strip()
        if not text:
            return
        async with websockets.connect(TTS_WS_URL) as tts_ws:
            await tts_ws.send(json.dumps({"text": text}))
            async for message in tts_ws:
                if isinstance(message, bytes):
                    yield message
                else:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "end":
                            break
                    except Exception:
                        pass
    except Exception:
        pass


@app.websocket("/ws/tts")
async def ws_tts_proxy(websocket: WebSocket):
    await websocket.accept()
    await proxy_tts_ws(websocket, TTS_WS_URL)


@app.post("/api/echo-bytes")
async def echo_bytes(
    request: Request, sr: int = 16000, ch: int = 1, fmt: str = "s16le"
):
    if sr != 16000 or ch != 1 or fmt != "s16le":
        raise HTTPException(
            status_code=400, detail="Only sr=16000, ch=1, fmt=s16le supported"
        )

    pcm_data = await request.body()
    if not pcm_data:
        raise HTTPException(status_code=400, detail="Empty body")
    return StreamingResponse(
        echo_bytes_stream(pcm_data), media_type="application/octet-stream"
    )


@app.post("/api/tts-segments")
async def tts_segments(request: Request):
    try:
        data = await request.json()
        segments = data.get("segments", [])
        if not segments:
            raise HTTPException(status_code=400, detail="segments required")
        text = " ".join(seg.get("text", "") for seg in segments if seg.get("text"))
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text in segments")
        return StreamingResponse(
            tts_segments_stream(text), media_type="application/octet-stream"
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


async def tts_segments_stream(text: str) -> AsyncGenerator[bytes, None]:
    try:
        async with websockets.connect(TTS_WS_URL) as tts_ws:
            await tts_ws.send(json.dumps({"text": text}))
            async for message in tts_ws:
                if isinstance(message, bytes):
                    yield message
                else:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "end":
                            break
                    except Exception:
                        pass
    except Exception:
        pass


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
