from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from tts_service.app.main import app

client = TestClient(app)


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@patch("tts_service.app.main.TTS")  # ← патчим именно как импортируется в main.py
def test_ws_tts_success(mock_tts_class):
    # Мок TTS
    mock_tts = MagicMock()
    mock_tts.tts.return_value = [0.0, 0.1, -0.1]
    mock_tts_class.return_value = mock_tts

    with client.websocket_connect("/ws/tts") as ws:
        ws.send_json({"text": "Hello"})
        data = ws.receive_bytes()
        assert data is not None
        end_msg = ws.receive_json()
        assert end_msg.get("type") == "end"


def test_ws_tts_empty_text():
    with client.websocket_connect("/ws/tts") as ws:
        ws.send_json({"text": ""})
        msg = ws.receive_json()
        assert "error" in msg
