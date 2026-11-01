"""
check_demo.py — run this before every demo (2026-10-28).

    cd backend
    venv\\Scripts\\activate
    python check_demo.py

In about a minute it checks everything the live demo needs, on the network
you are on right now, and asks real questions through the whole pipeline:

  1. The API keys are set in .env          (values are never printed)
  2. MongoDB Atlas is reachable            (and saves the offline copy)
  3. Groq is reachable                     (intent + reply model)
  4. Sarvam is reachable                   (Kannada voice)
  5. Real questions get real answers       ("Who is the principal?" ...)
  6. Kannada answers on every topic keep their facts exact (2026-10-29):
     each Kannada reply is compared with the English answer it came from
     (amounts, ranks, names, phone numbers AND which label each belongs to),
     with the time taken by every step.

All ✅  -> the demo will answer.
Any ❌  -> the line says what to fix (often: switch to a phone hotspot).
The backend server does NOT need to be running for this check.
"""

import asyncio
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

OK, BAD, WARN = "✅", "❌", "⚠️ "
results = []          # (passed: bool, essential: bool)

QUESTIONS = [
    ("Who is the principal?", "en"),
    ("What is the CSE fee for KCET?", "en"),
    # website data added on 2026-10-29
    ("Who is the vice principal?", "en"),
    ("Who are the trustees of SVIT?", "en"),
    ("Who is Dr. Vrinda Shetty?", "en"),
    ("Who are the faculty in AIML?", "en"),
    ("Which bus goes to Yelahanka?", "en"),
    ("What is the driver's phone number for route 1?", "en"),
    ("What documents are needed for KCET admission?", "en"),
]

# One Kannada question per topic (spoken style, as parents ask).
KANNADA_QUESTIONS = [
    ("fees", "CSE ge fees eshtu?"),
    ("cutoff", "AIML ge KCET cutoff rank eshtu?"),
    ("principal", "Principal yaaru?"),
    ("HOD", "CSE HOD yaaru?"),
    ("placements", "Placement alli highest package eshtu?"),
    ("hostel", "Girls hostel fee eshtu?"),
    ("transport", "Yelahanka inda bus fee eshtu?"),
    ("scholarship", "Scholarship sigutta?"),
    ("contact", "Admission office phone number enu?"),
    ("seats", "CSE alli eshtu seats ide?"),
]


def line(mark: str, text: str) -> None:
    print(f"  {mark} {text}", flush=True)


def check(passed: bool, text_ok: str, text_bad: str, essential: bool = True) -> bool:
    line(OK if passed else (BAD if essential else WARN), text_ok if passed else text_bad)
    results.append((passed, essential))
    return passed


def step(title: str) -> None:
    print(f"\n{title}", flush=True)


async def main() -> int:
    print("IntelliVoice — pre-demo check")
    print("=" * 40)

    # 1. keys -------------------------------------------------------------
    step("1. API keys in .env")
    for key in ("MONGODB_URL", "GROQ_API_KEY", "SARVAM_API_KEY", "SECRET_KEY"):
        check(bool(os.getenv(key)), f"{key} is set", f"{key} is missing from .env")

    # 2. MongoDB ----------------------------------------------------------
    step("2. MongoDB Atlas (college data)")
    from database import connection
    from engines import knowledge_engine
    await connection.connect_to_mongo()
    db = connection.get_database()
    started = time.perf_counter()
    try:
        await db.command("ping")
        check(True, f"reachable ({time.perf_counter() - started:.1f} s)", "")
        counts = await knowledge_engine.save_offline_copy()
        check(True, f"offline copy saved: {len(counts)} collections, {sum(counts.values())} records", "")
    except Exception as e:
        offline = os.path.isdir(knowledge_engine.OFFLINE_DIR) and any(
            n.endswith(".json") for n in os.listdir(knowledge_engine.OFFLINE_DIR))
        check(False, "", f"NOT reachable on this network ({type(e).__name__}). "
                         "Fix: phone hotspot, or Atlas > Network Access > Add current IP.", essential=not offline)
        check(offline, "offline copy found — answers will still work",
              "no offline copy yet — run this check once on a network where Atlas works (e.g. home)")

    # 3. Groq -------------------------------------------------------------
    step("3. Groq (understanding + replies)")
    try:
        from groq import Groq
        started = time.perf_counter()
        Groq(api_key=os.getenv("GROQ_API_KEY")).chat.completions.create(
            model="openai/gpt-oss-20b", max_tokens=20,
            messages=[{"role": "user", "content": "Reply with the word OK."}])
        check(True, f"reachable ({time.perf_counter() - started:.1f} s)", "")
    except Exception as e:
        check(False, "", f"NOT reachable ({type(e).__name__}: {str(e)[:80]}). Check the internet / GROQ_API_KEY.")

    # 4. Sarvam -----------------------------------------------------------
    step("4. Sarvam (Kannada voice)")
    try:
        from engines.tts_engine import synthesize_speech
        started = time.perf_counter()
        tts = synthesize_speech("ನಮಸ್ಕಾರ, ನಾನು ಇಂಟೆಲಿವಾಯ್ಸ್.", "kn")
        check(tts.get("success", False), f"voice OK ({time.perf_counter() - started:.1f} s)",
              f"voice failed ({tts.get('error', '')[:80]}). Check the internet / SARVAM_API_KEY.")
    except Exception as e:
        check(False, "", f"voice failed ({type(e).__name__}: {str(e)[:80]})")

    # 5. Real questions ---------------------------------------------------
    step("5. Real questions through the whole pipeline (loading models, ~30 s)...")
    try:
        from routes.voice import answer
        for question, lang in QUESTIONS:
            started = time.perf_counter()
            result = await answer(session_id=f"check-{time.time()}", text=question, include_audio=False,
                                  reply_language=lang)
            reply = (result.get("response_text") or "").replace("\n", " ")
            intent = (result.get("analysis") or {}).get("intent")
            found = (result.get("knowledge") or {}).get("found")
            no_info = "don't have that information" in reply or "ಮಾಹಿತಿ ಸದ್ಯಕ್ಕೆ" in reply
            check(bool(reply) and found and not no_info,
                  f"\"{question}\" -> {intent} ({time.perf_counter() - started:.1f} s): {reply[:90]}",
                  f"\"{question}\" -> {intent}: no proper answer ({reply[:80]})")
    except Exception as e:
        check(False, "", f"pipeline error: {type(e).__name__}: {str(e)[:120]}")

    # 6. Kannada on every topic --------------------------------------------
    step("6. Kannada answers on every topic (facts checked against the English answer)")
    print("     (each line: path used · time per step · the reply)", flush=True)
    try:
        from routes.voice import answer
        slow = []
        for topic, question in KANNADA_QUESTIONS:
            started = time.perf_counter()
            result = await answer(session_id=f"check-kn-{time.time()}", text=question, include_audio=True,
                                  reply_language="kn")
            total = time.perf_counter() - started
            debug = result.get("debug") or {}
            pipe = debug.get("kannada_pipeline") or {}
            t = debug.get("timings_ms") or {}
            steps = " ".join(f"{k}={v / 1000:.1f}s" for k, v in t.items()
                             if k in ("generate", "translate", "polish", "translate_2", "polish_2", "direct", "tts"))
            reply = (result.get("response_text") or "").replace("\n", " ")
            found = (result.get("knowledge") or {}).get("found")
            no_info = "ಮಾಹಿತಿ ಸದ್ಯಕ್ಕೆ" in reply or "don't have that information" in reply
            path = pipe.get("fact_check") or debug.get("path") or "?"
            if total > 12:
                slow.append(topic)
            if not reply or not found or no_info:
                check(False, "", f"[{topic}] \"{question}\" -> no proper answer ({reply[:70]})")
            elif pipe.get("fallback") == "english":
                check(False, "", f"[{topic}] Kannada facts didn't match, so the reply was given in ENGLISH "
                                 f"({path[:90]})", essential=False)
            else:
                check(True, f"[{topic}] {total:.1f}s · {path} · {steps}\n       {reply[:110]}", "")
            for r in pipe.get("fact_check_rejected") or []:
                line("  ", f"   rejected on the way: {r[:110]}")
        if slow:
            line(WARN, "slow (over 12 s): " + ", ".join(slow) + " — see the step times above")
        print("\n     Facts are checked automatically. Grammar is not: please LISTEN to a few Kannada replies.")
    except Exception as e:
        check(False, "", f"Kannada test error: {type(e).__name__}: {str(e)[:120]}")

    # summary -------------------------------------------------------------
    print("\n" + "=" * 40)
    failed = [r for r in results if not r[0] and r[1]]
    if failed:
        print(f"{BAD} NOT READY — fix the {len(failed)} line(s) marked {BAD} above, then run this again.")
        return 1
    print(f"{OK} READY FOR THE DEMO")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")   # Windows terminals: show ✅ and Kannada text
    except Exception:
        pass
    sys.exit(asyncio.run(main()))
