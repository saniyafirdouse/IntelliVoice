"""
DIAGNOSTIC ONLY — Full logging pass for ST vs Groq hybrid threshold analysis.

Does NOT modify intelligence_engine.py or any production classification
logic. Runs both classifiers on EVERY query (not just failures) across
both datasets, and logs full detail to a CSV for analysis:

    query, dataset, expected_intent,
    st_intent, st_confidence, st_correct,
    groq_intent, groq_correct,
    agree, at_least_one_correct

This is the data needed to derive an evidence-based confidence threshold
for the ST+Groq hybrid — not an arbitrary guess.

Usage (from backend/ folder, venv active):
    python tests/log_hybrid_data.py
"""

import asyncio
import csv
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from engines.language_engine import process_text_input
from engines.intelligence_engine import classify_intent as classify_embedding
from engines.groq_intent_classifier import classify_intent_groq


DATASETS = {
    "100_regression": os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "test_queries.json"),
    "40_generalization": os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "test_queries_generalization.json"),
}

OUTPUT_CSV = os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "hybrid_analysis_log.csv")


async def run_logging():
    rows = []

    for dataset_name, path in DATASETS.items():
        with open(path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)

        print(f"\nProcessing {dataset_name} ({len(test_cases)} queries)...")

        for i, case in enumerate(test_cases):
            query = case["query"]
            expected = case["expected_intent"]

            lang_result = await process_text_input(query)
            st_result = await classify_embedding(
                text=lang_result["raw_text"],
                normalized_text=lang_result["normalized_text"],
                language=lang_result["language"]["primary"]
            )
            st_intent = st_result["intent"]
            st_confidence = st_result["confidence"]

            groq_result = await classify_intent_groq(query)
            groq_intent = groq_result["intent"]

            st_correct = (st_intent == expected)
            groq_correct = (groq_intent == expected)
            agree = (st_intent == groq_intent)

            rows.append({
                "query": query,
                "dataset": dataset_name,
                "expected_intent": expected,
                "st_intent": st_intent,
                "st_confidence": st_confidence,
                "st_correct": st_correct,
                "groq_intent": groq_intent,
                "groq_correct": groq_correct,
                "agree": agree,
                "at_least_one_correct": st_correct or groq_correct,
            })

            print(f"  [{i+1}/{len(test_cases)}] ST={st_intent}({st_confidence}) "
                  f"Groq={groq_intent} agree={agree} "
                  f"st_ok={st_correct} groq_ok={groq_correct}")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Logged {len(rows)} rows to {OUTPUT_CSV}")

    # ── Quick summary stats printed immediately ────────────────────────
    total = len(rows)
    st_correct_n = sum(1 for r in rows if r["st_correct"])
    groq_correct_n = sum(1 for r in rows if r["groq_correct"])
    agree_n = sum(1 for r in rows if r["agree"])
    agree_correct_n = sum(1 for r in rows if r["agree"] and r["st_correct"])
    disagree_n = total - agree_n
    disagree_st_right = sum(1 for r in rows if not r["agree"] and r["st_correct"])
    disagree_groq_right = sum(1 for r in rows if not r["agree"] and r["groq_correct"])
    disagree_both_wrong = sum(1 for r in rows if not r["agree"] and not r["st_correct"] and not r["groq_correct"])

    print("\n" + "=" * 60)
    print("QUICK SUMMARY")
    print("=" * 60)
    print(f"Total queries:              {total}")
    print(f"ST accuracy:                {st_correct_n}/{total} ({st_correct_n/total*100:.1f}%)")
    print(f"Groq accuracy:              {groq_correct_n}/{total} ({groq_correct_n/total*100:.1f}%)")
    print(f"Agreement rate:             {agree_n}/{total} ({agree_n/total*100:.1f}%)")
    print(f"When agree, correct:        {agree_correct_n}/{agree_n} ({agree_correct_n/max(agree_n,1)*100:.1f}%)")
    print(f"Disagreement cases:         {disagree_n}")
    print(f"  → ST was right:           {disagree_st_right}")
    print(f"  → Groq was right:         {disagree_groq_right}")
    print(f"  → Both wrong:             {disagree_both_wrong}")

    print("\nST confidence when ST is CORRECT on disagreement cases:")
    for r in rows:
        if not r["agree"] and r["st_correct"]:
            print(f"  {r['st_confidence']}  —  {r['query'][:60]}")

    print("\nST confidence when ST is WRONG on disagreement cases:")
    for r in rows:
        if not r["agree"] and not r["st_correct"]:
            print(f"  {r['st_confidence']}  —  {r['query'][:60]}")


if __name__ == "__main__":
    asyncio.run(run_logging())