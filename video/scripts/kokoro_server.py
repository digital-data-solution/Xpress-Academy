#!/usr/bin/env python
"""Persistent Kokoro TTS HTTP server — loads the model ONCE and serves
many requests, instead of kokoro_tts.py's per-call subprocess spawn
(which reloads torch + the model fresh every single scene). Diagnosed
overnight during the big render batch: repeated OOM kills traced back
to that reload spike stacking on top of Remotion's own Chrome memory,
over and over, ~150 times. A resident server removes that repeated
spike entirely.

Started once (by scripts/batch_render.sh, or by hand) and left running
for an entire batch. src/tts/kokoro.ts talks to it over HTTP and falls
back to the one-shot subprocess (kokoro_tts.py) if the server isn't
reachable, so a standalone `npm run render:sample` still works with
nothing extra running.

Usage: python kokoro_server.py [--port 8765]
"""
import argparse
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import soundfile as sf
from kokoro import KPipeline

PIPELINES = {}  # lang_code -> KPipeline, built lazily, kept resident for the process's life


def get_pipeline(lang_code):
    if lang_code not in PIPELINES:
        print(f"Loading Kokoro pipeline (lang={lang_code})...", flush=True)
        PIPELINES[lang_code] = KPipeline(lang_code=lang_code)
    return PIPELINES[lang_code]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet — the batch log doesn't need one line per HTTP request

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
            text = body.get("text", "")
            voice = body.get("voice", "af_heart")
            lang_code = body.get("lang", "a")

            if not text.strip():
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"empty text")
                return

            pipeline = get_pipeline(lang_code)
            chunks = [audio for _graphemes, _phonemes, audio in pipeline(text, voice=voice)]
            full = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]

            buf = io.BytesIO()
            sf.write(buf, full, 24000, format="WAV")
            wav_bytes = buf.getvalue()

            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(wav_bytes)))
            self.end_headers()
            self.wfile.write(wav_bytes)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    # Warm the default English pipeline immediately rather than on first
    # request, so the first real scene of the batch isn't the one paying
    # the one-time load cost.
    get_pipeline("a")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Kokoro server ready on http://127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
