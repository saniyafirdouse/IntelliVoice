"""
Generates MESSY, realistic training examples for MuRIL fine-tuning —
the "tired parent phone call" register (rambling, indirect, code-switched,
filler words) — to sit ALONGSIDE the clean intents.json examples in
training. This directly addresses the distribution-mismatch risk: a
model trained only on clean text learns to recognize clean text, not
how people actually speak.

Efficient by design: ONE Groq call generates 8-10 messy variants PLUS
their language/emotion labels for an entire intent at once — ~45 calls
total instead of ~450, so this should fit in a single day's quota.

Same safe patterns as label_data.py: pre-flight check, resumable,
saves after every intent, full log file.

Run from backend/ folder, venv active:
    python tests/muril/generate_messy_examples.py
"""

import asyncio
import csv
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from engines.groq_intent_classifier import client, MODEL

INTENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "database", "seed_data", "intents.json"
)
OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "database", "seed_data", "muril_training"
)
CSV_PATH = os.path.join(OUTPUT_DIR, "messy_examples.csv")
LOG_PATH = os.path.join(OUTPUT_DIR, "messy_generation_log.txt")

FIELDNAMES = [
    "intent_id", "category", "text",
    "groq_language", "groq_emotion", "label_success",
    "human_language", "human_emotion", "reviewed",
]

VARIANTS_PER_INTENT = 9
BETWEEN_CALL_DELAY = 0.5

GENERATION_PROMPT = """You are generating realistic training data for a voice assistant used by tired, busy parents calling a college admissions office — NOT a formal FAQ writer.

Intent: {intent_id}
What this intent means: {description}
Clean example questions already covering this intent (for context only — do NOT just rephrase these lightly):
{clean_examples}

Generate {n} NEW, DIFFERENT ways a real parent or student might ask about this SAME topic over a phone call, following these rules:
- Rambling and conversational — include hesitation, filler words, unnecessary context, incomplete grammar
- At least half should mix English with Hindi or Kannada naturally (code-switched, not two separate clean sentences)
- Vary emotional tone realistically: some plain/neutral, some anxious/worried, some frustrated, some confused
- Avoid literally reusing phrases from the clean examples above
- Each one must still clearly be asking about the SAME topic ({intent_id})

For EACH variant, also classify:
- "language": primary language — exactly one of en, hi, kn
- "emotion": exactly one of neutral, worried, confused, frustrated, excited

Respond with ONLY a JSON array like this, nothing else:
[
  {{"text": "...", "language": "en", "emotion": "worried"}},
  {{"text": "...", "language": "hi", "emotion": "neutral"}}
]
"""


def log(message: str):
    print(message)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def next_reset_time() -> str:
    now_utc = datetime.now(timezone.utc)
    tomorrow_midnight_utc = (now_utc + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    ist_offset = timedelta(hours=5, minutes=30)
    reset_ist = tomorrow_midnight_utc + ist_offset
    return (f"{tomorrow_midnight_utc.strftime('%Y-%m-%d %H:%M UTC')} "
            f"(= {reset_ist.strftime('%Y-%m-%d %H:%M')} IST)")


def load_done_intents() -> set:
    if not os.path.exists(CSV_PATH):
        return set()
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["intent_id"] for r in rows}


def append_rows(new_rows: list):
    file_exists = os.path.exists(CSV_PATH)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)


async def generate_for_intent(intent: dict) -> dict:
    sample_examples = "\n".join(f"- {e}" for e in intent["examples"][:4])
    prompt = GENERATION_PROMPT.format(
        intent_id=intent["id"],
        description=intent["description"],
        clean_examples=sample_examples,
        n=VARIANTS_PER_INTENT,
    )
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            max_tokens=2048,
        )


        raw = response.choices[0].message.content
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            log(f"  ⚠️ [{intent['id']}] Groq response had no JSON array. Raw response:")
            log(f"     {raw[:300]}")
            return {"success": False, "still_limited": False, "variants": []}
        try:
            variants = json.loads(match.group(0))
        except json.JSONDecodeError as je:
            log(f"  ⚠️ [{intent['id']}] JSON parse failed: {je}")
            log(f"     Raw matched text: {match.group(0)[:300]}")
            return {"success": False, "still_limited": False, "variants": []}
        return {"success": True, "variants": variants}

    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str or "429" in error_str:
            return {"success": False, "still_limited": True, "variants": []}
        log(f"  ⚠️ Error on {intent['id']}: {error_str[:100]}")
        return {"success": False, "still_limited": False, "variants": []}


async def preflight_check(intents: list) -> bool:
    log("Running pre-flight check (1 tiny test call)...")
    test_intent = intents[0]
    result = await generate_for_intent(test_intent)
    if result.get("still_limited"):
        log(f"\n🛑 Quota already exhausted. Next reset: {next_reset_time()}")
        return False
    if result["success"] and result["variants"]:
        log("✅ Quota available — proceeding with the real run.\n")
        rows = [{
            "intent_id": test_intent["id"], "category": test_intent["category"],
            "text": v["text"], "groq_language": v.get("language", "en"),
            "groq_emotion": v.get("emotion", "neutral"), "label_success": "True",
            "human_language": "", "human_emotion": "", "reviewed": "",
        } for v in result["variants"]]
        append_rows(rows)
        log(f"  [{test_intent['id']}] {len(rows)} messy variants generated")
        return True
    log("❌ Pre-flight generation failed for a non-quota reason (see error above).")
    return False


async def main():
    log(f"\n{'='*60}\nRun started: {datetime.now().isoformat()}\n{'='*60}")

    with open(INTENTS_PATH, "r", encoding="utf-8") as f:
        intents = json.load(f)

    done_intents = load_done_intents()
    remaining = [i for i in intents if i["id"] not in done_intents]

    log(f"{len(intents)} total intents | {len(done_intents)} already done | {len(remaining)} remaining")

    if not remaining:
        log("\n🎉 All intents already have messy examples generated!")
        log("   Next: review messy_examples.csv, then merge with candidate_labels.csv")
        return

    if not done_intents:
        if not await preflight_check(remaining):
            return
        remaining = remaining[1:]

    hit_wall = False
    completed_count = 0

    for intent in remaining:
        result = await generate_for_intent(intent)

        if result.get("still_limited"):
            hit_wall = True
            break

        if result["success"] and result["variants"]:
            rows = [{
                "intent_id": intent["id"], "category": intent["category"],
                "text": v["text"], "groq_language": v.get("language", "en"),
                "groq_emotion": v.get("emotion", "neutral"), "label_success": "True",
                "human_language": "", "human_emotion": "", "reviewed": "",
            } for v in result["variants"]]
            append_rows(rows)
            completed_count += 1
            log(f"  [{intent['id']}] {len(rows)} messy variants generated ({completed_count}/{len(remaining)} intents this run)")
        else:
            log(f"  ⚠️ [{intent['id']}] generation failed, will retry on next run")

        await asyncio.sleep(BETWEEN_CALL_DELAY)

    still_remaining = len(remaining) - completed_count
    log(f"\n✅ {completed_count} intents processed this run")
    log(f"   {still_remaining} intents still remaining")

    if hit_wall:
        log(f"\n⏳ Hit today's quota. Next reset: {next_reset_time()}")
        log("   Run this exact same command after that time.")
    elif still_remaining == 0:
        log("\n🎉 All done! Next: review messy_examples.csv, then merge with candidate_labels.csv")

    log(f"\nFull history: {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())