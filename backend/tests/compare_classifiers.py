"""
Head-to-head comparison: Sentence Transformers (production) vs Groq
(experimental) intent classification, run against BOTH evaluation sets:

    1. test_queries.json                  — 100 queries (contaminated with
                                              training examples — treat this
                                              as a regression/plumbing test)
    2. test_queries_generalization.json   — 40 queries (verified zero
                                              overlap with intents.json —
                                              this is the real generalization
                                              test, and the one that matters
                                              most for this comparison)

Does NOT modify or touch intelligence_engine.py's production classifier.
Purely diagnostic — run this, read the output, decide.

Usage (from backend/ folder, venv active):
    python tests/compare_classifiers.py
"""

import asyncio
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from engines.language_engine import process_text_input
from engines.intelligence_engine import classify_intent as classify_embedding
from engines.groq_intent_classifier import classify_intent_groq


DATASETS = {
    "test_queries.json (100 — contaminated/regression)":
        os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "test_queries.json"),
    "test_queries_generalization.json (40 — held-out/real test)":
        os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "test_queries_generalization.json"),
}


async def run_comparison():
    overall_results = {}

    for dataset_name, path in DATASETS.items():
        with open(path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)

        embedding_correct = 0
        groq_correct = 0
        both_correct = 0
        both_wrong = 0
        embedding_only = 0
        groq_only = 0

        disagreements = []

        for case in test_cases:
            query = case["query"]
            expected = case["expected_intent"]

            lang_result = await process_text_input(query)
            embed_result = await classify_embedding(
                text=lang_result["raw_text"],
                normalized_text=lang_result["normalized_text"],
                language=lang_result["language"]["primary"]
            )
            embed_intent = embed_result["intent"]

            groq_result = await classify_intent_groq(query)
            groq_intent = groq_result["intent"]

            embed_ok = (embed_intent == expected)
            groq_ok = (groq_intent == expected)

            if embed_ok:
                embedding_correct += 1
            if groq_ok:
                groq_correct += 1

            if embed_ok and groq_ok:
                both_correct += 1
            elif not embed_ok and not groq_ok:
                both_wrong += 1
            elif embed_ok and not groq_ok:
                embedding_only += 1
            elif groq_ok and not embed_ok:
                groq_only += 1

            if embed_intent != groq_intent or not (embed_ok and groq_ok):
                disagreements.append({
                    "query": query,
                    "expected": expected,
                    "embedding": embed_intent,
                    "embedding_confidence": embed_result.get("confidence"),
                    "groq": groq_intent,
                    "embed_correct": embed_ok,
                    "groq_correct": groq_ok,
                })

        total = len(test_cases)
        print("=" * 75)
        print(f"DATASET: {dataset_name}")
        print("=" * 75)
        print(f"Total queries:                    {total}")
        print(f"Sentence Transformers accuracy:   {embedding_correct}/{total}  ({embedding_correct/total*100:.1f}%)")
        print(f"Groq (experimental) accuracy:      {groq_correct}/{total}  ({groq_correct/total*100:.1f}%)")
        print()
        print(f"Both correct:                      {both_correct}")
        print(f"Both wrong:                         {both_wrong}")
        print(f"Only Sentence Transformers correct: {embedding_only}")
        print(f"Only Groq correct:                  {groq_only}")
        print()

        if disagreements:
            print(f"--- {len(disagreements)} DISAGREEMENT / FAILURE CASES ---\n")
            for d in disagreements:
                marker_e = "✅" if d["embed_correct"] else "❌"
                marker_g = "✅" if d["groq_correct"] else "❌"
                print(f"Query: {d['query']}")
                print(f"  Expected:              {d['expected']}")
                print(f"  Sentence Transformers: {d['embedding']}  {marker_e}  (conf: {d['embedding_confidence']})")
                print(f"  Groq:                  {d['groq']}  {marker_g}")
                print("-" * 60)
            print()

        overall_results[dataset_name] = {
            "total": total,
            "embedding_accuracy": embedding_correct / total * 100,
            "groq_accuracy": groq_correct / total * 100,
        }

    print("=" * 75)
    print("FINAL SUMMARY")
    print("=" * 75)
    for name, r in overall_results.items():
        print(f"{name}")
        print(f"   Sentence Transformers: {r['embedding_accuracy']:.1f}%")
        print(f"   Groq (experimental):   {r['groq_accuracy']:.1f}%")
        print()


if __name__ == "__main__":
    asyncio.run(run_comparison())