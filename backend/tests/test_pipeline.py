"""
End-to-end test — full pipeline (Engine 1 -> 2 -> 3 -> 5) against your
REAL MongoDB, Groq and Sarvam, without starting the server.

Uses the same run_pipeline() the API routes use, so a pass here means
/voice/query and /voice/text will behave the same way.

Loads Whisper, MuRIL and Sentence Transformers at startup (slow the
first time — same as starting the server).

Usage (from backend/ folder, venv active):
    python tests/test_pipeline.py                # all text + audio cases
    python tests/test_pipeline.py --no-audio     # skip TTS (faster)
    python tests/test_pipeline.py --text-only    # skip the 3 .wav input files
    python tests/test_pipeline.py --case 2       # one case by number

Reply audio is saved to tests/output_audio/pipeline_<n>_<lang>.wav
"""

import argparse
import asyncio
import os
import sys
import time
import uuid

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(BACKEND_DIR)

from database.connection import close_mongo_connection, connect_to_mongo  # noqa: E402
from engines.language_engine import process_text_input, transcribe_audio  # noqa: E402
from engines.tts_engine import save_wav  # noqa: E402
from routes.voice import run_pipeline  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_audio")

# (description, input, script)  — input is text, or "wav:<file>" for audio
CASES = [
    ("EN fee, ambiguous (should list all CSE options)", "What is the CSE fee?", None),
    ("HI fee via KCET", "CSE ka KCET se fee kitna hai?", None),
    ("KN fee via KCET (Kannada script)", "CSE fee KCET alli eshtu?", None),
    ("KN fee via KCET (romanized display)", "CSE fee KCET alli eshtu?", "romanized"),
    ("KN worried parent", "Nanna maga marks kadime ide, CSE alli manage maadtana? Tumba tension aagide", None),
    ("EN comparison", "What is the difference between CSE and AIML?", None),
    ("EN greeting", "Hello", None),
    ("HI out-of-scope", "Aaj mausam kaisa hai?", None),
    ("EN topic with no data yet (expect honest 'not available')", "Is there a hostel for girls?", None),
    ("AUDIO English test file", "wav:test_english.wav", None),
    ("AUDIO Hindi test file", "wav:test_hindi.wav", None),
    ("AUDIO Kannada test file", "wav:test_kannada.wav", None),
    # ── Kannada / English mix checks (added 2026-10-06) ──────────────────
    # Reply should mirror the user's words: English only where the user
    # used it, names/numbers, and the allowed college words.
    ("KN user says 'duddu' — reply should say ದುಡ್ಡು, fee 325000",
     "Management quota alli CSE ge eshtu duddu aagutte?", None),
    ("KN worried parent, almost all Kannada — reply should use ಚಿಂತೆ, little English",
     "Nanna magalu modala sala mane bittu hostel ge hogtidale, tumba chinte aagtide", None),
    ("KN English-heavy user — reply may keep placement/average/package",
     "Placement record hegide? Average package eshtu?", None),
    ("KN typed in Kannada script (entity names may not be recognised)",
     "ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್ ಗೆ ಕೆಸಿಇಟಿ ಮೂಲಕ ಎಷ್ಟು ಫೀಸ್?", None),
]


async def run_case(n, desc, user_input, script, include_audio):
    print("=" * 72)
    print(f"[{n}] {desc}")

    start = time.perf_counter()
    if user_input.startswith("wav:"):
        path = os.path.join(BACKEND_DIR, user_input[4:])
        if not os.path.exists(path):
            print(f"SKIPPED — {path} not found")
            return None
        with open(path, "rb") as f:
            language_result = await transcribe_audio(f.read(), os.path.basename(path))
        input_type = "audio"
    else:
        language_result = await process_text_input(user_input)
        input_type = "text"
    language_ms = int((time.perf_counter() - start) * 1000)

    if not language_result["success"]:
        print(f"ENGINE 1 FAILED: {language_result.get('error')}")
        return None

    result = await run_pipeline(
        language_result, session_id=str(uuid.uuid4()), input_type=input_type,
        script=script, include_audio=include_audio, language_ms=language_ms,
    )

    a = result["analysis"]
    print(f"HEARD/TYPED: {result['transcribed_text']}")
    print(f"Language:  {result['language']['primary']}   Script: {result['script']}")
    print(f"Intent:    {a['intent']} ({a['confidence']}, {a['confidence_zone']})  "
          f"emotion={a['emotion']}  mode={a['response_mode']}")
    print(f"Entities:  {a['entities']}")
    print(f"Knowledge: {result['knowledge']}")
    print(f"\nRESPONSE:\n{result['response_text']}")
    if result["response_text_native"] != result["response_text"]:
        print(f"\nSPOKEN (native script):\n{result['response_text_native']}")
    print(f"\nTimings (ms): {result['timings_ms']}   status={result['status']}")
    if result["debug"].get("error"):
        print(f"ERROR: {result['debug']['error']}")

    if include_audio:
        if result["tts_success"]:
            out = os.path.join(OUTPUT_DIR, f"pipeline_{n:02d}_{result['language']['primary']}.wav")
            save_wav(result["audio_base64"], out)
            print(f"AUDIO: saved {out}")
        else:
            print(f"AUDIO: FAILED — {result['debug'].get('tts_error')}")
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--text-only", action="store_true")
    parser.add_argument("--case", type=int)
    args = parser.parse_args()

    include_audio = not args.no_audio
    if include_audio:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    await connect_to_mongo()
    results = []
    try:
        for n, (desc, user_input, script) in enumerate(CASES, 1):
            if args.case and n != args.case:
                continue
            if args.text_only and user_input.startswith("wav:"):
                continue
            results.append(await run_case(n, desc, user_input, script, include_audio))
    finally:
        await close_mongo_connection()

    ran = [r for r in results if r]
    print("=" * 72)
    print(f"Completed: {sum(r['status'] == 'complete' for r in ran)}/{len(ran)}"
          + (f"   Audio: {sum(r['tts_success'] for r in ran)}/{len(ran)}" if include_audio else ""))
    print("Check: right intent per query, fee answers match MongoDB, "
          "'not available' only where data is genuinely missing.")


if __name__ == "__main__":
    asyncio.run(main())
