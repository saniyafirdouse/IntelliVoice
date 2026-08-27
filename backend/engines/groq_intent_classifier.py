"""
EXPERIMENTAL — Groq-based Intent Classifier
"""

import json
import os
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "openai/gpt-oss-20b" 

INTENTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "database", "seed_data", "intents.json"
)
with open(INTENTS_PATH, "r", encoding="utf-8") as f:
    INTENTS = json.load(f)

VALID_INTENT_IDS = {intent["id"] for intent in INTENTS}

INTENT_LIST_BLOCK = "\n".join(
    f"- {intent['id']}: {intent['description']}"
    for intent in INTENTS
)

SYSTEM_PROMPT = f"""You are an intent classifier for IntelliVoice, a college admissions voice assistant.

Given a user's query, classify it into EXACTLY ONE of the following intents:

{INTENT_LIST_BLOCK}

Respond with ONLY a JSON object in this exact format: {{"intent": "intent_id_here"}}
The intent_id MUST be exactly one of the IDs listed above.
If the query is a greeting only, use "greet".
If the query is unrelated to college admissions entirely, use "fallback".
"""


def _extract_json(raw_text: str) -> dict:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}


async def classify_intent_groq(text: str) -> dict:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        parsed = _extract_json(raw)
        intent = parsed.get("intent", "").strip()

        if intent not in VALID_INTENT_IDS:
            print(f"⚠️  Invalid intent returned: '{intent}' for query: '{text[:50]}...'")
            return {"intent": "fallback", "success": True, "note": f"invalid: {intent}"}

        return {"intent": intent, "success": True}

    except Exception as e:
        # PRINT loudly this time — no silent failures
        print(f"❌ GROQ API ERROR on query '{text[:50]}...': {type(e).__name__}: {e}")
        return {"intent": "fallback", "success": False, "error": str(e)}