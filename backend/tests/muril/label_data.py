"""
ONE script for labeling — safe to run this exact same command every
single day until it's done. No separate "generate" vs "resume" files.

- First run: labels everything from scratch
- Every run after: automatically skips anything already labeled,
  only spends today's quota on what's still missing
- Hits the daily quota wall -> stops immediately, no wasted retries
- Full history always in labeling_log.txt (never rely on terminal
  scrollback)

Run from backend/ folder, venv active, every day until finished:
    python tests/muril/label_data.py
"""

import asyncio
import csv
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from engines.groq_intent_classifier import client, MODEL, _extract_json

INTENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "database", "seed_data", "intents.json"
)
OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "database", "seed_data", "muril_training"
)
CSV_PATH = os.path.join(OUTPUT_DIR, "candidate_labels.csv")
LOG_PATH = os.path.join(OUTPUT_DIR, "labeling_log.txt")

FIELDNAMES = [
    "intent_id", "category", "text",
    "groq_language", "groq_emotion", "label_success",
    "human_language", "human_emotion", "reviewed",
]

BETWEEN_CALL_DELAY = 0.3

LABEL_PROMPT = """Classify this sentence on two dimensions.

1. language — the PRIMARY language being spoken: exactly one of en, hi, kn
   - Romanized Hindi/Kannada (written in English letters) still counts as hi/kn, not en

2. emotion — exactly one of: neutral, worried, confused, frustrated, excited

Sentence: "{text}"

Respond with ONLY this JSON: {{"language": "...", "emotion": "..."}}
"""


def log(message: str):
    print(message)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def load_existing_rows() -> dict:
    """Returns {text: row_dict} for whatever's already in the CSV,
    or empty dict if this is the first run ever."""
    if not os.path.exists(CSV_PATH):
        return {}
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["text"]: r for r in rows}


def build_full_row_list() -> list:
    """Builds the complete 1166-row target list from intents.json,
    merging in any already-existing labels so nothing already done
    gets lost or re-sent."""
    with open(INTENTS_PATH, "r", encoding="utf-8") as f:
        intents = json.load(f)

    existing = load_existing_rows()
    all_rows = []

    for intent in intents:
        for text in intent["examples"]:
            if text in existing:
                all_rows.append(existing[text])  # keep whatever we already have
            else:
                all_rows.append({
                    "intent_id": intent["id"], "category": intent["category"], "text": text,
                    "groq_language": "", "groq_emotion": "", "label_success": "",
                    "human_language": "", "human_emotion": "", "reviewed": "",
                })
    return all_rows


async def label_one(text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": LABEL_PROMPT.format(text=text)}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        parsed = _extract_json(raw)
        language = parsed.get("language", "en").strip()
        emotion = parsed.get("emotion", "neutral").strip()

        if language not in {"en", "hi", "kn"}:
            language = "en"
        if emotion not in {"neutral", "worried", "confused", "frustrated", "excited"}:
            emotion = "neutral"

        return {"language": language, "emotion": emotion, "success": True}

    except Exception as e:
        error_str = str(e)
        if "rate_limit" in error_str or "429" in error_str:
            return {"success": False, "still_limited": True}
        log(f"  ⚠️ Error: {error_str[:100]}")
        return {"language": "en", "emotion": "neutral", "success": False, "still_limited": False}


def next_reset_time() -> str:
    """TPD resets at a fixed midnight UTC, not a rolling window from
    last usage. Compute exactly when that next reset is, in both UTC
    and IST for convenience."""
    from datetime import timedelta, timezone
    now_utc = datetime.now(timezone.utc)
    tomorrow_midnight_utc = (now_utc + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    ist_offset = timedelta(hours=5, minutes=30)
    reset_ist = tomorrow_midnight_utc + ist_offset
    return (f"{tomorrow_midnight_utc.strftime('%Y-%m-%d %H:%M UTC')} "
            f"(= {reset_ist.strftime('%Y-%m-%d %H:%M')} IST)")


async def preflight_check() -> bool:
    """One minimal, near-zero-token call to check whether the quota is
    available RIGHT NOW, before committing to a loop over hundreds of
    real examples. Costs almost nothing even if it fails."""
    log("Running pre-flight check (1 tiny test call)...")
    result = await label_one("test")
    if result.get("still_limited"):
        log(f"\n🛑 Quota already exhausted — confirmed BEFORE starting the real run.")
        log(f"   Next reset: {next_reset_time()}")
        log(f"   No real labeling calls were made. Nothing wasted.")
        return False
    log("✅ Quota available — proceeding with the real run.\n")
    return True


def save_all(rows: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


async def main():
    log(f"\n{'='*60}\nRun started: {datetime.now().isoformat()}\n{'='*60}")

    if not await preflight_check():
        return  # stop here — zero real calls made, nothing wasted

    all_rows = build_full_row_list()
    remaining = [r for r in all_rows if r["label_success"] not in ("True", "true")]

    log(f"{len(all_rows)} total examples | {len(all_rows) - len(remaining)} already labeled | {len(remaining)} remaining")

    if not remaining:
        log("\n🎉 Everything is already labeled! Ready for review, then finalize_labels.py")
        return

    fixed_count = 0
    hit_wall = False

    for i, row in enumerate(remaining):
        result = await label_one(row["text"])

        if result.get("still_limited"):
            hit_wall = True
            break

        row["groq_language"] = result["language"]
        row["groq_emotion"] = result["emotion"]
        row["label_success"] = "True" if result["success"] else "False"
        if result["success"]:
            fixed_count += 1

        save_all(all_rows)  # save progress after EVERY row — never lose work

        if (i + 1) % 25 == 0:
            log(f"  [{i+1}/{len(remaining)}] processed this run... ({fixed_count} succeeded)")

        await asyncio.sleep(BETWEEN_CALL_DELAY)

    save_all(all_rows)

    still_remaining = sum(1 for r in all_rows if r["label_success"] not in ("True", "true"))
    log(f"\n✅ {fixed_count} labeled successfully this run")
    log(f"   {still_remaining} still remaining")

    if hit_wall:
        log(f"\n⏳ Hit today's quota mid-run. Next reset: {next_reset_time()}")
        log("   Run this exact same command after that time — it will")
        log("   automatically continue from where it stopped.")
    elif still_remaining == 0:
        log("\n🎉 All done! Next: review candidate_labels.csv, then run finalize_labels.py")

    log(f"\nFull history: {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())