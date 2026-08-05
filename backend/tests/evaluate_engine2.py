"""
Engine 2 Evaluation Script
Run this any time you change intelligence_engine.py or language_engine.py
to see if accuracy improved or regressed.

Usage (from backend/ folder, with venv active):
    python tests/evaluate_engine2.py
"""

import json
import os
import sys
import asyncio

# Allow importing from the backend root when running this file directly
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from engines.language_engine import process_text_input
from engines.intelligence_engine import classify_intent


TEST_FILE = os.path.join(os.path.dirname(__file__), "..", "database", "seed_data", "test_queries.json")


def entities_match(expected: dict, actual: dict) -> bool:
    """
    An entity check passes if every key/value pair in `expected`
    is present in `actual`. Extra keys in `actual` (e.g. null values
    for entities not mentioned) are fine — we only check what was
    expected to be found.
    """
    if not expected:
        return True
    for key, value in expected.items():
        actual_value = actual.get(key)
        if actual_value is None:
            return False
        # Case-insensitive string comparison, exact match for numbers
        if isinstance(value, str) and isinstance(actual_value, str):
            if value.lower() != actual_value.lower():
                return False
        elif value != actual_value:
            return False
    return True


async def run_evaluation():
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    total = len(test_cases)
    intent_correct = 0
    emotion_correct = 0
    language_correct = 0
    entity_correct = 0

    failures = []

    for case in test_cases:
        query = case["query"]
        expected_intent = case["expected_intent"]
        expected_emotion = case.get("emotion", "neutral")
        expected_language = case.get("language", "en")
        expected_entities = case.get("entities", {})

        # Run through Engine 1 (language processing) then Engine 2 (intelligence)
        lang_result = await process_text_input(query)
        result = await classify_intent(
    text=lang_result["raw_text"],
    normalized_text=lang_result["normalized_text"],
    language=lang_result["language"]["primary"]
)

        actual_intent = result["intent"]
        actual_emotion = result["emotion"]
        actual_language = lang_result["language"]["primary"]
        actual_entities = result["entities"]

        intent_ok = (actual_intent == expected_intent)
        emotion_ok = (actual_emotion == expected_emotion)
        language_ok = (actual_language == expected_language)
        entities_ok = entities_match(expected_entities, actual_entities)

        if intent_ok:
            intent_correct += 1
        if emotion_ok:
            emotion_correct += 1
        if language_ok:
            language_correct += 1
        if entities_ok:
            entity_correct += 1

        if not (intent_ok and emotion_ok and entities_ok):
            failures.append({
                "query": query,
                "expected_intent": expected_intent,
                "actual_intent": actual_intent,
                "confidence": result.get("confidence"),
                "confidence_zone": result.get("confidence_zone"),
                "expected_emotion": expected_emotion,
                "actual_emotion": actual_emotion,
                "expected_language": expected_language,
                "actual_language": actual_language,
                "expected_entities": expected_entities,
                "actual_entities": actual_entities,
            })

    print("=" * 60)
    print("ENGINE 2 EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total test queries:     {total}")
    print(f"Intent accuracy:        {intent_correct}/{total}  ({intent_correct/total*100:.1f}%)")
    print(f"Emotion accuracy:       {emotion_correct}/{total}  ({emotion_correct/total*100:.1f}%)")
    print(f"Language accuracy:      {language_correct}/{total}  ({language_correct/total*100:.1f}%)")
    print(f"Entity accuracy:        {entity_correct}/{total}  ({entity_correct/total*100:.1f}%)")
    print("=" * 60)

    if failures:
        print(f"\n{len(failures)} FAILED CASES:\n")
        for f in failures:
            print(f"Query: {f['query']}")
            print(f"  Intent:   expected={f['expected_intent']!r}  actual={f['actual_intent']!r}  "
                  f"(confidence={f['confidence']}, zone={f['confidence_zone']})")
            print(f"  Emotion:  expected={f['expected_emotion']!r}  actual={f['actual_emotion']!r}")
            print(f"  Language: expected={f['expected_language']!r}  actual={f['actual_language']!r}")
            print(f"  Entities: expected={f['expected_entities']}  actual={f['actual_entities']}")
            print("-" * 60)
    else:
        print("\nNo failures — all test cases passed.")


if __name__ == "__main__":
    asyncio.run(run_evaluation())