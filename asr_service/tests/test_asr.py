from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from asr_service.app.main import app
import numpy as np

client = TestClient(app)


def test_healthz_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stt_empty_body_returns_400():
    r = client.post("/api/stt/bytes", data=b"")
    assert r.status_code == 400
    assert "Empty" in r.text


@patch(
    "asr_service.app.main.WhisperModel"
)  # ← патчим именно как импортируется в main.py
def test_stt_success(mock_whisper):
    # Настраиваем мок модели
    mock_model = MagicMock()
    mock_whisper.return_value = mock_model

    seg_mock = MagicMock()
    seg_mock.text = "hello"
    seg_mock.start = 0.0
    seg_mock.end = 1.2
    mock_model.transcribe.return_value = ([seg_mock], {"language": "en"})

    pcm_data = (np.zeros(16000, dtype="<i2")).tobytes()

    r = client.post("/api/stt/bytes", data=pcm_data)
    assert r.status_code == 200
    j = r.json()
    assert j["text"] == "hello"
    assert len(j["segments"]) == 1
    assert j["segments"][0]["start_ms"] == 0
