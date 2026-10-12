"""
Speed test — measures what a parent actually experiences, the way the
app will work with play-as-you-go audio:

  1. POST /voice/query with include_audio=false  -> reply TEXT is ready
  2. POST /voice/speak for every speech chunk, all at the same time
       -> FIRST SOUND = when chunk 1's audio arrives (the app starts playing)
       -> FULL AUDIO  = when all chunks have arrived

The server must be running (uvicorn main:app). From backend/, venv active:
    python tests/test_speed.py q1.mp4                 # one recording (Kannada)
    python tests/test_speed.py a.mp4 b.mp4 c.mp4      # several
    python tests/test_speed.py q1.mp4 --language en   # other language
    python tests/test_speed.py --text "What is the CSE fee?"

Each reply's audio is saved next to the recording as <name>_reply.wav.
"""

import argparse
import base64
import io
import os
import sys
import time
import wave
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# 127.0.0.1, not "localhost": on Windows "localhost" first tries IPv6, which
# the server is not listening on, and waits ~2 s before falling back.
URL = "http://127.0.0.1:8000/voice"


def merge_wavs(clips: list) -> bytes:
    out = io.BytesIO()
    with wave.open(io.BytesIO(clips[0]), "rb") as first:
        params = first.getparams()
    with wave.open(out, "wb") as w:
        w.setparams(params)
        for clip in clips:
            with wave.open(io.BytesIO(clip), "rb") as r:
                w.writeframes(r.readframes(r.getnframes()))
    return out.getvalue()


def run(label: str, files=None, data=None, save_as=None):
    print("=" * 72)
    print(label)
    started = time.perf_counter()
    r = requests.post(f"{URL}/query", files=files, data=data, timeout=120)
    text_ready = time.perf_counter() - started
    if r.status_code != 200:
        print(f"ERROR {r.status_code}: {r.text[:300]}")
        return
    r = r.json()
    L, A = r.get("language", {}), r.get("analysis", {})
    if L.get("stt_raw_text") is not None:
        print(f"WHISPER  : {L.get('stt_raw_text')}")
        print(f"FIXED    : {r.get('transcribed_text')}")
        print(f"FIXES    : {L.get('transcript_fixes')}  rejected: {L.get('transcript_fixes_rejected')}")
    else:
        print(f"TYPED    : {r.get('transcribed_text')}")
    print(f"INTENT   : {A.get('intent')} | emotion: {A.get('emotion')} | entities: {A.get('entities')}")
    print(f"KNOWLEDGE: {r.get('knowledge')}")
    print(f"REPLY    : {r.get('response_text')}")

    chunks, lang = r.get("speech_chunks") or [], r.get("speech_language")
    first_sound = full_audio = None
    clips = [None] * len(chunks)
    pieces = [None] * len(chunks)
    audio_start = time.perf_counter()
    if chunks:
        with ThreadPoolExecutor(max_workers=len(chunks)) as pool:
            futures = {pool.submit(requests.post, f"{URL}/speak",
                                   data={"text": c, "language": lang}, timeout=60): i
                       for i, c in enumerate(chunks)}
            for fut in as_completed(futures):
                i = futures[fut]
                resp = fut.result()
                if resp.status_code == 200:
                    body = resp.json()
                    clips[i] = base64.b64decode(body["audio_base64"])
                    pieces[i] = (time.perf_counter() - audio_start, body.get("tts_ms"), len(chunks[i]))
                    if i == 0:
                        first_sound = time.perf_counter() - started
                else:
                    print(f"  chunk {i + 1} audio failed: {resp.status_code} {resp.text[:150]}")
        full_audio = time.perf_counter() - started

    print(f"STEPS ms : {r.get('timings_ms')} | engine-5: {r.get('debug', {}).get('timings_ms')}"
          f" | early start used: {r.get('debug', {}).get('early_start_used')}")
    print("-" * 72)
    print(f"  TEXT READY  : {text_ready:5.1f} s")
    if first_sound is not None:
        print(f"  FIRST SOUND : {first_sound:5.1f} s   <- when the parent starts hearing the answer")
    print(f"  FULL AUDIO  : {full_audio:5.1f} s   ({len(chunks)} pieces)" if full_audio else "  (no audio)")
    # Per piece: if Sarvam's own time is short but pieces arrive one after
    # another, requests are waiting in line; if Sarvam's time is long for
    # every piece, Sarvam itself is slow from this connection.
    for i, info in enumerate(pieces):
        if info:
            arrived, sarvam_ms, n = info
            print(f"     piece {i + 1}: {n:>3} chars | Sarvam {sarvam_ms} ms | arrived {arrived:.1f} s after text")

    if save_as and all(clips):
        with open(save_as, "wb") as f:
            f.write(merge_wavs(clips))
        print(f"  saved {save_as}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("recordings", nargs="*")
    p.add_argument("--language", default="kn", choices=["en", "hi", "kn"])
    p.add_argument("--text")
    args = p.parse_args()
    if not args.recordings and not args.text:
        p.print_help()
        sys.exit(1)

    for path in args.recordings:
        if not os.path.exists(path):
            print(f"Not found: {path}")
            continue
        with open(path, "rb") as f:
            audio = f.read()
        run(f"{path}  (language={args.language})",
            files={"audio": (os.path.basename(path), audio)},
            data={"language": args.language, "include_audio": "false"},
            save_as=os.path.splitext(path)[0] + "_reply.wav")
    if args.text:
        run(f"typed: {args.text}", data={"text": args.text, "include_audio": "false"},
            save_as="typed_reply.wav")


if __name__ == "__main__":
    main()
