"""
Bulk-fixes the specific, confirmed pattern found during review: Kannada
yes/no questions ending in casual tags (ideya, sigutta, hege, etc.) were
being mislabeled 'confused' by Groq when they are just neutral factual
questions. This applies the correction directly to human_emotion +
reviewed, leaving groq_emotion untouched as a record of what Groq
originally said.

Run from backend/ folder:
    python tests/muril/fix_kannada_confused_labels.py
"""

import csv
import os

CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "database", "seed_data",
    "muril_training", "candidate_labels.csv"
)

KANNADA_Q_TAGS = ['enittu', 'ideya', 'hege', 'hegide', 'enu', 'eshtu', 'sigutta', 'agutta', 'irutta']
REAL_CONFUSION_WORDS = ['gothilla', 'artha', 'confuse', 'samajh nahi', 'clear nahi',
                        'dont understand', "don't understand", 'dont know', "don't know"]


def is_false_confused(text: str) -> bool:
    t = text.lower().rstrip('?').strip()
    ends_with_tag = any(t.endswith(tag) for tag in KANNADA_Q_TAGS)
    has_real_confusion = any(w in t for w in REAL_CONFUSION_WORDS)
    return ends_with_tag and not has_real_confusion


def main():
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    fixed = []
    for row in rows:
        if row["groq_emotion"] == "confused" and is_false_confused(row["text"]):
            row["human_emotion"] = "neutral"
            row["reviewed"] = "bulk_fix_kannada_question_tag"
            fixed.append(row["text"])

    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Fixed {len(fixed)} rows — human_emotion set to 'neutral', reviewed flagged.")
    print("   (groq_emotion left as-is, so the original guess is still visible for reference)\n")
    for t in fixed:
        print(f"  - {t}")


if __name__ == "__main__":
    main()