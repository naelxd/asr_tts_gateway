import argparse
import wave
import numpy as np
import requests


def read_wav_as_pcm_s16le_mono16k(path: str) -> bytes:
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        frames = wf.getnframes()
        raw = wf.readframes(frames)

    if sw == 2:
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sw == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128) / 128.0
    else:
        raise ValueError("Only 8-bit or 16-bit WAV supported")

    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    elif ch != 1:
        raise ValueError("Only mono or stereo WAV supported")

    target_sr = 16000
    if sr != target_sr:
        src_len = x.shape[0]
        dst_len = int(round(src_len * (target_sr / sr)))
        xp = np.linspace(0.0, 1.0, src_len, endpoint=False)
        x = np.interp(np.linspace(0.0, 1.0, dst_len, endpoint=False), xp, x).astype(
            np.float32
        )

    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    return pcm


def main():
    parser = argparse.ArgumentParser(description="Gateway echo-bytes client")
    parser.add_argument(
        "--url", default="http://localhost:8000/api/echo-bytes", help="Gateway endpoint"
    )
    parser.add_argument("--wav", default="input.wav", help="Input WAV file path")
    parser.add_argument("--out", default="out_echo.wav", help="Output WAV file path")
    args = parser.parse_args()

    pcm = read_wav_as_pcm_s16le_mono16k(args.wav)

    params = {"sr": 16000, "ch": 1, "fmt": "s16le"}
    resp = requests.post(
        args.url,
        params=params,
        data=pcm,
        headers={"Content-Type": "application/octet-stream"},
        timeout=60,
        stream=True,
    )
    resp.raise_for_status()

    with wave.open(args.out, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)

        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:
                wf.writeframes(chunk)

    print(f"Saved echo result to {args.out}")


if __name__ == "__main__":
    main()
