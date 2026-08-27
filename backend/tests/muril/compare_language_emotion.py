"""
Head-to-head comparison: current production language/emotion detection
(py3langid + keyword-based emotion) vs. fine-tuned multi-task MuRIL,
run against BOTH evaluation sets.

Does NOT modify any production code. Purely diagnostic.

Usage (from backend/ folder, venv active):
    python tests/muril/compare_language_emotion.py
"""

import asyncio
import json
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from engines.language_engine import process_text_input
from engines.intelligence_engine import detect_emotion  # current keyword-based detector
from engines.muril_multitask_classifier import classify_language_emotion_muril


DATASETS = {
    "test_queries.json (100)":
        os.path.join(os.path.dirname(__file__), "..", "..", "database", "seed_data", "test_queries.json"),
    "test_queries_generalization.json (40)":
        os.path.join(os.path.dirname(__file__), "..", "..", "database", "seed_data", "test_queries_generalization.json"),
}


async def run_comparison():
    for dataset_name, path in DATASETS.items():
        with open(path, "r", encoding="utf-8") as f:
            test_cases = json.load(f)

        old_lang_correct = old_emo_correct = 0
        muril_lang_correct = muril_emo_correct = 0
        total = len(test_cases)
        disagreements = []

        for case in test_cases:
            query = case["query"]
            expected_lang = case.get("language", "en")
            expected_emo = case.get("emotion", "neutral")

            # Current production system
            lang_result = await process_text_input(query)
            old_lang = lang_result["language"]["primary"]
            old_emo = detect_emotion(query)

            # Fine-tuned MuRIL
            muril_result = await classify_language_emotion_muril(query)
            muril_lang = muril_result["language"]
            muril_emo = muril_result["emotion"]

            old_lang_ok = (old_lang == expected_lang)
            old_emo_ok = (old_emo == expected_emo)
            muril_lang_ok = (muril_lang == expected_lang)
            muril_emo_ok = (muril_emo == expected_emo)

            if old_lang_ok: old_lang_correct += 1
            if old_emo_ok: old_emo_correct += 1
            if muril_lang_ok: muril_lang_correct += 1
            if muril_emo_ok: muril_emo_correct += 1

            if old_lang_ok != muril_lang_ok or old_emo_ok != muril_emo_ok:
                disagreements.append({
                    "query": query, "expected_lang": expected_lang, "expected_emo": expected_emo,
                    "old_lang": old_lang, "muril_lang": muril_lang,
                    "old_emo": old_emo, "muril_emo": muril_emo,
                })

        print("=" * 75)
        print(f"DATASET: {dataset_name}")
        print("=" * 75)
        print(f"Total queries: {total}\n")
        print(f"LANGUAGE — production (py3langid): {old_lang_correct}/{total} ({old_lang_correct/total*100:.1f}%)")
        print(f"LANGUAGE — fine-tuned MuRIL:        {muril_lang_correct}/{total} ({muril_lang_correct/total*100:.1f}%)\n")
        print(f"EMOTION  — production (keywords):   {old_emo_correct}/{total} ({old_emo_correct/total*100:.1f}%)")
        print(f"EMOTION  — fine-tuned MuRIL:         {muril_emo_correct}/{total} ({muril_emo_correct/total*100:.1f}%)\n")

        if disagreements:
            print(f"--- {len(disagreements)} cases where the two systems disagree ---\n")
            for d in disagreements:
                print(f"Query: {d['query']}")
                print(f"  Language: expected={d['expected_lang']}  old={d['old_lang']}  muril={d['muril_lang']}")
                print(f"  Emotion:  expected={d['expected_emo']}  old={d['old_emo']}  muril={d['muril_emo']}")
                print("-" * 60)
        print()


if __name__ == "__main__":
    asyncio.run(run_comparison())