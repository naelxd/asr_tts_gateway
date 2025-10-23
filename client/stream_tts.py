import argparse
import asyncio
import json
import time
import wave

import websockets


async def stream_tts(uri: str, text: str, out_path: str, sr: int = 16000, ch: int = 1):
    start_time = time.time()
    try:
        async with websockets.connect(uri, timeout=10) as ws:
            print(f"Connected to {uri}")
            await ws.send(json.dumps({"text": text}))
            print(f"Sent text: '{text[:50]}{'...' if len(text) > 50 else ''}'")

            with wave.open(out_path, "wb") as wf:
                wf.setnchannels(ch)
                wf.setsampwidth(2)  # s16le
                wf.setframerate(sr)

                bytes_received = 0
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=3 * 60)
                        if isinstance(msg, (bytes, bytearray)):
                            wf.writeframes(msg)
                            bytes_received += len(msg)
                        else:
                            try:
                                payload = json.loads(msg)
                                if payload.get("type") == "end":
                                    print("Received end signal")
                                    break
                                if "error" in payload:
                                    raise RuntimeError(payload["error"])
                            except json.JSONDecodeError:
                                # Ignore non-JSON text frames
                                pass
                    except asyncio.TimeoutError:
                        print("Timeout waiting for message")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        print("Connection closed by server")
                        break

    except Exception as e:
        print(f"Error: {e}")
        raise

    elapsed = time.time() - start_time
    print(f"Saved {bytes_received} bytes to {out_path}. Elapsed: {elapsed:.2f}s")


def main():
    parser = argparse.ArgumentParser(description="Stream TTS client")
    parser.add_argument(
        "--uri", default="ws://localhost:8082/ws/tts", help="TTS WS endpoint"
    )
    parser.add_argument("--text", default="Hello from minimal TTS", help="Input text")
    parser.add_argument("--out", default="out.wav", help="Output WAV path")
    parser.add_argument("--sr", type=int, default=16000, help="Sample rate")
    parser.add_argument("--ch", type=int, default=1, help="Channels")
    args = parser.parse_args()

    asyncio.run(stream_tts(args.uri, args.text, args.out, sr=args.sr, ch=args.ch))


if __name__ == "__main__":
    main()
