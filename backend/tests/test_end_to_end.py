"""
End-to-end verification — Engine 2 (classify_intent) + Engine 3 (fetch_knowledge)
run against REAL data Bhuvana has inserted into MongoDB.

Not an automated pass/fail test — this prints results so you can manually
verify the right document(s) actually come back for each query. Run this
any time new collections get populated, to sanity-check before moving on.

Usage (from backend/ folder, venv active):
    python tests/test_end_to_end.py
"""

import asyncio
import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from database.connection import connect_to_mongo, close_mongo_connection
from engines.language_engine import process_text_input
from engines.intelligence_engine import classify_intent
from engines.knowledge_engine import fetch_knowledge


TEST_QUERIES = [
    # fees — deliberately ambiguous (no exam/quota) to confirm multi-match works
    "CSE fee kitni hai?",
    # fees — specific channel, should return exactly one document
    "What is the CSE fee through KCET?",

    # cutoffs
    "What is the KCET cutoff for CSE?",

    # admissions — one per topic, confirms topic filtering actually separates them
    "What is the admission process?",
    "What documents are required for management quota?",
    "What is the KCET application deadline?",
    "How can I check my admission status?",
    "Are seats available in CSE?",

    # branches
    "What is the difference between CSE and AIML?",

    # recruiters — tests the new 84-company entity list
    "Does Microsoft visit the campus?",
    "Does Boeing recruit from SVIT?",
]


async def run_tests():
    await connect_to_mongo()

    for query in TEST_QUERIES:
        print("=" * 70)
        print(f"QUERY: {query}")
        print("-" * 70)

        lang_result = await process_text_input(query)
        engine2_result = await classify_intent(
            text=lang_result["raw_text"],
            normalized_text=lang_result["normalized_text"],
            language=lang_result["language"]["primary"]
        )

        print(f"Intent:            {engine2_result['intent']}  (confidence: {engine2_result['confidence']}, zone: {engine2_result['confidence_zone']})")
        print(f"Entities:          {engine2_result['entities']}")
        print(f"Knowledge request: {engine2_result['knowledge_request']}")

        knowledge_result = await fetch_knowledge(engine2_result)

        print(f"\nFOUND: {knowledge_result['found']}")
        if knowledge_result["found"]:
            print(f"Match type: {knowledge_result.get('match_type')}")
            print("Data returned:")
            print(json.dumps(knowledge_result["data"], indent=2, default=str))
        else:
            print(f"Reason: {knowledge_result.get('reason')}")
        print()

    await close_mongo_connection()
    print("=" * 70)
    print("Review each block above — confirm the RIGHT data came back for each query.")


if __name__ == "__main__":
    asyncio.run(run_tests())