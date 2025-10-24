# gateway/tests/test_gateway.py
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

from gateway.app.main import app  # ← теперь путь к FastAPI-приложению

client = TestClient(app)


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_echo_bytes_empty_body_returns_400():
    r = client.post("/api/echo-bytes")
    assert r.status_code == 400
    assert "Empty" in r.text


@patch("gateway.app.main.websockets.connect")
@patch("gateway.app.main.requests.post")
def test_echo_bytes_success(mock_post, mock_ws_connect):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "text": "hello world",
        "segments": [{"start_ms": 0, "end_ms": 1000, "text": "hello"}],
    }

    mock_ws = AsyncMock()

    async def fake_iter():
        yield b"pcm_chunk"
        yield b'{"type":"end"}'

    mock_ws.__aiter__.side_effect = lambda: fake_iter()
    mock_ws_connect.return_value.__aenter__.return_value = mock_ws

    pcm_data = b"\x00" * 3200
    r = client.post("/api/echo-bytes", data=pcm_data)
    assert r.status_code == 200
    assert b"pcm_chunk" in r.content


@patch("gateway.app.main.websockets.connect")
@patch("gateway.app.main.requests.post", side_effect=Exception("ASR failed"))
def test_echo_bytes_asr_exception(mock_post, mock_ws_connect):
    mock_ws = mock_ws_connect.return_value.__enter__.return_value
    mock_ws.__aiter__ = lambda: iter([])
    mock_ws.send = MagicMock()
    mock_ws.send_text = MagicMock()

    pcm_data = b"\x00" * 3200
    r = client.post("/api/echo-bytes", data=pcm_data)
    assert r.status_code == 200
    assert r.content == b""


def test_tts_segments_invalid_json_returns_400():
    r = client.post("/api/tts-segments", data=b"{notjson")
    assert r.status_code == 400


@patch("gateway.app.main.websockets.connect")
def test_tts_segments_valid_request(mock_ws_connect):
    mock_ws = AsyncMock()

    async def fake_iter():
        yield b"chunk"
        yield b'{"type":"end"}'

    mock_ws.__aiter__.side_effect = lambda: fake_iter()
    mock_ws_connect.return_value.__aenter__.return_value = mock_ws

    data = {"segments": [{"text": "Hello"}]}
    r = client.post("/api/tts-segments", json=data)
    assert r.status_code == 200
    assert b"chunk" in r.content


@patch("gateway.app.main.websockets.connect", side_effect=Exception("TTS failed"))
def test_tts_segments_tts_exception(mock_ws):
    data = {"segments": [{"text": "Hi"}]}
    r = client.post("/api/tts-segments", json=data)
    assert r.status_code == 200
    assert r.content == b""
