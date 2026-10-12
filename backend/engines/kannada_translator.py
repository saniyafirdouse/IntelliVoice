"""
English -> Kannada translation using Sarvam AI (Mayura model).

Replaces the earlier Google Translate approach — Sarvam is purpose-built
for Indian languages, including natural code-mixed/colloquial output,
which produced noticeably better results in direct testing.

Same function signature as before, so response_engine.py's integration
(translate_to_kannada -> _polish_kannada) needs no further changes.

2026-10-02: longer responses are now split at sentence boundaries
before translation, since Mayura rejects inputs above its size limit
(long comparison answers could hit it). Short inputs behave exactly
as before — one API call.

Requires:
    pip install sarvamai
And SARVAM_API_KEY set in .env
"""

import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

from engines.tts_engine import split_text

load_dotenv()

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

# "code-mixed" mode confirmed via testing to produce the best base
# quality — the remaining English-ratio adjustment happens in the
# Groq refinement step (_polish_kannada) afterward, not here.
MODE = "code-mixed"

# Mayura's per-request input limit is about 1000 characters.
MAX_CHARS_PER_REQUEST = 900


def translate_to_kannada(text: str) -> str:
    """
    Translates English text to natural, code-mixed Kannada.
    Returns None on failure — caller must handle that explicitly.
    """
    try:
        parts = []
        for chunk in split_text(text, MAX_CHARS_PER_REQUEST):
            response = client.text.translate(
                input=chunk,
                source_language_code="en-IN",
                target_language_code="kn-IN",
                model="mayura:v1",
                mode=MODE,
            )
            parts.append(response.translated_text)
        result = " ".join(p.strip() for p in parts if p).strip()
        return result or None

    except Exception as e:
        print(f"❌ Sarvam translation error: {e}")
        return None
