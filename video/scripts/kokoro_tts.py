#!/usr/bin/env python
"""Kokoro-82M TTS sidecar for the Remotion pipeline (../src/tts/kokoro.ts
shells out to this). A separate process rather than an in-Node model
because Kokoro is a PyTorch model with no maintained Node binding —
paying one process-spawn per scene is a fine trade for zero-cost, local,
license-clean TTS.

Usage:
    python kokoro_tts.py <output.wav> [--voice=af_heart] [--lang=a]
Narration text comes in on stdin (utf-8), not argv — avoids fighting
shell/PowerShell quoting over arbitrary lesson narration text.

One-time setup (also see ../README.md):
    pip install kokoro soundfile numpy
    # Kokoro shells out to espeak-ng for phonemization:
    #   Windows:      winget install eSpeak-NG.eSpeak-NG
    #   macOS:        brew install espeak-ng
    #   Debian/Ubuntu: apt-get install espeak-ng
Generate one line and listen to it before pointing a real render at this
— per the build doc's own "before you start" step. Not verified inside
this session: the sandbox this was written in has no espeak-ng install
and no audio output to confirm against.
"""
import argparse
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", help="Path to write the generated WAV to.")
    parser.add_argument("--voice", default="af_heart", help="Kokoro built-in voice name.")
    parser.add_argument("--lang", default="a", help="Kokoro lang_code (see kokoro's README for the table).")
    args = parser.parse_args()

    text = sys.stdin.read()
    if not text.strip():
        print("kokoro_tts.py: empty narration text on stdin", file=sys.stderr)
        sys.exit(1)

    pipeline = KPipeline(lang_code=args.lang)
    # Kokoro internally splits long text into multiple chunks (one per
    # sentence-ish unit) and yields each separately — concatenate them
    # into the one continuous file a scene's narration actually needs,
    # rather than just taking the first chunk.
    chunks = [audio for _graphemes, _phonemes, audio in pipeline(text, voice=args.voice)]
    if not chunks:
        print("kokoro_tts.py: Kokoro produced no audio chunks for this text", file=sys.stderr)
        sys.exit(1)

    full = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    sf.write(args.output, full, 24000)


if __name__ == "__main__":
    main()
