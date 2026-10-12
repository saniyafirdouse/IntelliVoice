"""
Standalone test — Engine 5 (response_engine.py) including voice output.

Runs Engine 5 by itself with hand-built Engine 2 / Engine 3 outputs, so
it needs NO MongoDB, and does not load Whisper / MuRIL / Sentence
Transformers. Uses real 2026-27 fee records from
database/seed_data/fees.json.

Calls the real Groq and Sarvam APIs (needs GROQ_API_KEY and
SARVAM_API_KEY in .env). Saves every spoken response as a .wav in
tests/output_audio/ so you can listen to it.

Usage (from backend/ folder, venv active):
    python tests/test_response_engine.py                 # all cases, with audio
    python tests/test_response_engine.py --no-audio      # text only (faster)
    python tests/test_response_engine.py --only kn       # just Kannada cases
    python tests/test_response_engine.py --case 4        # one case by number
"""

import argparse
import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from engines.response_engine import generate_response  # noqa: E402
from engines.tts_engine import save_wav  # noqa: E402

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_audio")

# Real records from fees.json
CSE_KCET = {"_id": "x1", "branch": "CSE", "exam": "KCET", "academic_year": "2026-27",
            "annual_fee": 120000, "semester_fee": 120000, "payment_mode": "One-time", "installments": 1}
CSE_COMEDK = {"_id": "x2", "branch": "CSE", "exam": "COMEDK", "academic_year": "2026-27",
              "annual_fee": 140000, "semester_fee": 140000, "payment_mode": "One-time", "installments": 1}
CSE_MGMT = {"_id": "x3", "branch": "CSE", "quota": "Management", "academic_year": "2026-27",
            "annual_fee": 325000, "semester_fee": 162500, "early_bird_fee": 275000,
            "payment_mode": "Semester-wise", "installments": 2}

SINGLE_KCET = {"found": True, "match_type": "single", "data": CSE_KCET}
MULTIPLE_CSE = {"found": True, "match_type": "multiple", "count": 3,
                "data": [CSE_MGMT, CSE_KCET, CSE_COMEDK]}
NOT_FOUND = {"found": False, "reason": "no_matching_document"}
BRANCHES = {"found": True, "match_type": "multiple", "count": 2, "data": [
    {"_id": "b1", "branch": "CSE", "full_name": "Computer Science and Engineering",
     "focus": "programming, algorithms, databases, operating systems, software engineering"},
    {"_id": "b2", "branch": "AIML", "full_name": "Artificial Intelligence and Machine Learning",
     "focus": "machine learning, deep learning, data science, neural networks"},
]}
# NOTE: BRANCHES is illustrative test data, not a real DB record.


def e2(query, language, intent, emotion="neutral", mode="informational", escalation=False):
    """Minimal Engine 2 output — only the fields Engine 5 reads."""
    return {"query": query, "language": language, "intent": intent, "emotion": emotion,
            "response_mode": mode, "needs_escalation": escalation}


CASES = [
    # (description, engine2_result, knowledge_result, script)
    ("EN fee, ambiguous -> must list all 3 options",
     e2("What is the CSE fee?", "en", "ask_fees_branch"), MULTIPLE_CSE, None),
    ("HI fee via KCET, default script (romanized Hinglish)",
     e2("CSE ka KCET se fee kitna hai?", "hi", "ask_fees_branch"), SINGLE_KCET, None),
    ("HI fee via KCET, Devanagari",
     e2("CSE ka KCET se fee kitna hai?", "hi", "ask_fees_branch"), SINGLE_KCET, "native"),
    ("KN fee via KCET, default script (Kannada script)",
     e2("CSE fee KCET alli eshtu?", "kn", "ask_fees_branch"), SINGLE_KCET, None),
    ("KN fee via KCET, romanized display (audio still from Kannada script)",
     e2("CSE fee KCET alli eshtu?", "kn", "ask_fees_branch"), SINGLE_KCET, "romanized"),
    ("KN worried parent, nothing in DB -> reassurance without apologising",
     e2("Nanna maga marks kadime ide, CSE alli manage maadtana? Tumba tension aagide",
        "kn", "ask_academic_support", emotion="worried", mode="reassurance"), NOT_FOUND, None),
    ("KN comparison CSE vs AIML",
     e2("CSE mattu AIML difference enu?", "kn", "ask_branch_difference", mode="comparison"), BRANCHES, None),
    ("EN greeting", e2("Hi", "en", "greet"), None, None),
    ("KN greeting (now via Sarvam pipeline)", e2("Namaskara", "kn", "greet"), None, None),
    ("HI out-of-scope -> polite redirect",
     e2("Aaj mausam kaisa hai?", "hi", "fallback"), None, None),
    ("EN worried + out-of-scope -> ESCALATION, not redirect",
     e2("Nobody answered my calls and I'm really worried about my son's seat",
        "en", "fallback", emotion="worried", mode="escalation", escalation=True), NOT_FOUND, None),
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--only", choices=["en", "hi", "kn"])
    parser.add_argument("--case", type=int)
    args = parser.parse_args()

    include_audio = not args.no_audio
    if include_audio:
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = []
    for n, (desc, engine2_result, knowledge_result, script) in enumerate(CASES, 1):
        if args.case and n != args.case:
            continue
        if args.only and engine2_result["language"] != args.only:
            continue

        print("=" * 72)
        print(f"[{n}] {desc}")
        print(f"QUERY: {engine2_result['query']}")
        print("-" * 72)

        start = time.time()
        result = await generate_response(engine2_result, knowledge_result,
                                         script=script, include_audio=include_audio)
        elapsed = time.time() - start

        print(f"RESPONSE ({result['language']}, {result['script']}):\n{result['response_text']}")
        if result["response_text_native"] != result["response_text"]:
            print(f"\nSPOKEN TEXT (native script):\n{result['response_text_native']}")
        print(f"\npath={result['debug']['path']}  success={result['success']}  "
              f"kannada_pipeline={result['debug']['kannada_pipeline']}  time={elapsed:.1f}s")
        if result["debug"]["error"]:
            print(f"ERROR: {result['debug']['error']}")

        if include_audio:
            if result["tts_success"]:
                path = os.path.join(OUTPUT_DIR, f"{n:02d}_{result['language']}_{result['script']}.wav")
                save_wav(result["audio_base64"], path)
                print(f"AUDIO: saved {path}")
            else:
                print(f"AUDIO: FAILED — {result['debug']['tts_error']}")

        results.append((n, result))
        print()

    print("=" * 72)
    ok = sum(1 for _, r in results if r["success"])
    tts_ok = sum(1 for _, r in results if r["tts_success"])
    print(f"Generated: {ok}/{len(results)}" + (f"   Audio: {tts_ok}/{len(results)}" if include_audio else ""))
    print("Now read each response and listen to the .wav files — check facts match "
          "the data, Kannada sounds natural, and case 11 escalates.")


if __name__ == "__main__":
    asyncio.run(main())
