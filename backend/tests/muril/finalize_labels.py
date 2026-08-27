"""
finalize_labels.py

Combines the two labeled datasets into ONE final training set for
MuRIL multi-task fine-tuning (language + emotion, two output heads,
one shared model).

Robust to either version of messy_examples.csv:
  - The final merged file (simple language/emotion columns), OR
  - A raw single-source generator output (groq_language/groq_emotion +
    optional human_language/human_emotion overrides)
This avoids breaking if the wrong-stage file is in place.

Run from backend/ folder:
    python tests/muril/finalize_labels.py
"""

import csv
import json
import os
import random
from collections import defaultdict, Counter

random.seed(42)

SEED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "database", "seed_data")
MURIL_TRAINING_DIR = os.path.join(SEED_DATA_DIR, "muril_training")
CANDIDATE_LABELS_PATH = os.path.join(MURIL_TRAINING_DIR, "candidate_labels.csv")
MESSY_EXAMPLES_PATH = os.path.join(MURIL_TRAINING_DIR, "messy_examples.csv")
OUTPUT_DIR = MURIL_TRAINING_DIR

VAL_SPLIT = 0.15
VALID_LANGUAGES = {"en", "hi", "kn"}
VALID_EMOTIONS = {"neutral", "worried", "confused", "frustrated", "excited"}


def load_candidate_labels() -> list:
    with open(CANDIDATE_LABELS_PATH, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    result = []
    overrides_applied = 0
    for r in rows:
        language = r.get("human_language", "").strip() or r["groq_language"].strip()
        emotion = r.get("human_emotion", "").strip() or r["groq_emotion"].strip()

        if r.get("human_language", "").strip() or r.get("human_emotion", "").strip():
            overrides_applied += 1

        if language not in VALID_LANGUAGES or emotion not in VALID_EMOTIONS:
            continue

        result.append({
            "text": r["text"], "language": language, "emotion": emotion,
            "intent_id": r["intent_id"], "source": "clean",
        })

    print(f"  candidate_labels.csv: {len(result)} usable rows ({overrides_applied} had human overrides applied)")
    return result


def load_messy_examples() -> list:
    with open(MESSY_EXAMPLES_PATH, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    has_simple_schema = "language" in rows[0] and "emotion" in rows[0]
    overrides_applied = 0
    result = []

    for r in rows:
        if has_simple_schema:
            language = r["language"].strip()
            emotion = r["emotion"].strip()
        else:
            language = r.get("human_language", "").strip() or r["groq_language"].strip()
            emotion = r.get("human_emotion", "").strip() or r["groq_emotion"].strip()
            if r.get("human_language", "").strip() or r.get("human_emotion", "").strip():
                overrides_applied += 1

        if language not in VALID_LANGUAGES or emotion not in VALID_EMOTIONS:
            continue

        result.append({
            "text": r["text"], "language": language, "emotion": emotion,
            "intent_id": r["intent_id"], "source": "messy",
        })

    schema_note = "simple (final merged) schema" if has_simple_schema else f"raw generator schema ({overrides_applied} overrides applied)"
    print(f"  messy_examples.csv: {len(result)} usable rows, detected {schema_note}")
    return result


def main():
    print("Loading source files...")
    clean_rows = load_candidate_labels()
    messy_rows = load_messy_examples()

    all_rows = clean_rows + messy_rows
    print(f"\nCombined total: {len(all_rows)} rows")

    language_map = {lang: i for i, lang in enumerate(sorted(VALID_LANGUAGES))}
    emotion_map = {emo: i for i, emo in enumerate(sorted(VALID_EMOTIONS))}

    by_intent = defaultdict(list)
    for row in all_rows:
        by_intent[row["intent_id"]].append(row)

    train_rows, val_rows = [], []
    for intent_id, rows in by_intent.items():
        random.shuffle(rows)
        n_val = max(1, int(len(rows) * VAL_SPLIT))
        val_rows.extend(rows[:n_val])
        train_rows.extend(rows[n_val:])

    random.shuffle(train_rows)
    random.shuffle(val_rows)

    def finalize(row):
        return {
            "text": row["text"],
            "language_label": language_map[row["language"]],
            "emotion_label": emotion_map[row["emotion"]],
            "language": row["language"],
            "emotion": row["emotion"],
            "intent_id": row["intent_id"],
            "source": row["source"],
        }

    train_final = [finalize(r) for r in train_rows]
    val_final = [finalize(r) for r in val_rows]

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "train.json"), "w", encoding="utf-8") as f:
        json.dump(train_final, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "val.json"), "w", encoding="utf-8") as f:
        json.dump(val_final, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "language_map.json"), "w", encoding="utf-8") as f:
        json.dump(language_map, f, indent=2)
    with open(os.path.join(OUTPUT_DIR, "emotion_map.json"), "w", encoding="utf-8") as f:
        json.dump(emotion_map, f, indent=2)

    print(f"\n✅ train.json: {len(train_final)} rows")
    print(f"✅ val.json: {len(val_final)} rows")
    print(f"✅ language_map.json: {language_map}")
    print(f"✅ emotion_map.json: {emotion_map}")

    print(f"\nTrain set breakdown:")
    print(f"  By source: {dict(Counter(r['source'] for r in train_final))}")
    print(f"  By language: {dict(Counter(r['language'] for r in train_final))}")
    print(f"  By emotion: {dict(Counter(r['emotion'] for r in train_final))}")

    print(f"\nAll files saved to: {OUTPUT_DIR}")
    print("\nNext step: upload this muril_training/ folder to Google Colab")
    print("and run the multi-task MuRIL training script.")


if __name__ == "__main__":
    main()