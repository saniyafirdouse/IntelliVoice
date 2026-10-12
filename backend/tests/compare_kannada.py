"""
Kannada side-by-side: the SAME English answer turned into Kannada two ways.

  A = translate_polish : Sarvam translation + 120B polish   (current default)
  B = direct           : 120B writes the Kannada in one step (~1 s faster)

Read both columns: if B is as good (correct facts, natural simple Kannada,
correct grammar), set KANNADA_PIPELINE = "direct" in
engines/response_engine.py. If not, keep "translate_polish".

No server needed. From backend/, venv active:
    python tests/compare_kannada.py
Results are also saved to tests/output_audio/compare_kannada.txt
"""

import asyncio
import os
import sys
import time

BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.append(BACKEND_DIR)

from database.connection import close_mongo_connection, connect_to_mongo  # noqa: E402
from engines import response_engine as R  # noqa: E402
from engines.language_engine import process_text_input  # noqa: E402
from routes.voice import _understand  # noqa: E402

QUESTIONS = [
    "CSE fee KCET alli eshtu?",
    "Management quota alli CSE ge eshtu duddu aagutte?",
    "Nanna maga marks kadime ide, CSE alli manage maadtana? Tumba tension aagide",
    "CSE mattu AIML ge enu vyatyasa?",
    "Nanna magalu modala sala mane bittu hostel ge hogtidale, tumba chinte aagtide",
    "ISE cutoff eshtu?",
]
PAUSE_BETWEEN = 20  # seconds — keeps under Groq's free-plan per-minute limit (~8K tokens/min per model)

OUT = os.path.join(os.path.dirname(__file__), "output_audio", "compare_kannada.txt")


async def english_answer(e2: dict, kr: dict) -> str:
    """Same path choice as generate_response()."""
    intent = e2.get("intent")
    query = e2.get("query", "")
    if intent == "greet":
        return await R._generate_simple(R.GREET_INSTRUCTION, "kn", "native", query)
    if (intent in R.BRANCH_SPECIFIC_INTENTS and not e2.get("needs_escalation")
            and not (e2.get("entities") or {}).get("branch")):
        return await R._generate_simple(R.ASK_BRANCH_INSTRUCTION, "kn", "native", query)
    if intent == "fallback" and not e2.get("needs_escalation"):
        return await R._generate_simple(R.FALLBACK_INSTRUCTION, "kn", "native", query)
    return await R._generate_grounded(e2, kr, "kn", "native")


async def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    lines = []

    def show(text=""):
        print(text)
        lines.append(text)

    await connect_to_mongo()
    totals = {"A": [], "B": []}
    try:
        for n, question in enumerate(QUESTIONS, 1):
            if n > 1:
                await asyncio.sleep(PAUSE_BETWEEN)
            lang = await process_text_input(question)
            lang["language"]["primary"] = "kn"
            understood = await _understand(lang)
            e2, kr = understood["intelligence"], understood["knowledge"]
            english = await english_answer(e2, kr)

            show("=" * 78)
            show(f"[{n}] {question}")
            show(f"    intent: {e2['intent']} | emotion: {e2['emotion']} | entities: {e2['entities']}")
            show(f"    ENGLISH: {english}")
            for key, mode in (("A", "translate_polish"), ("B", "direct")):
                start = time.perf_counter()
                out = await R._localize(english, "kn", "native", question, pipeline_mode=mode)
                ms = int((time.perf_counter() - start) * 1000)
                totals[key].append(ms)
                note = "" if mode != "direct" or out["kannada_pipeline"].get("direct") else "  (fell back to A)"
                show(f"  {key} {mode:<16} {ms:>5} ms{note}")
                show(f"     {out['speech_text']}")
    finally:
        await close_mongo_connection()

    show("=" * 78)
    for key in ("A", "B"):
        if totals[key]:
            show(f"  {key}: average {sum(totals[key]) // len(totals[key])} ms")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
