"""
English -> Kannada translation using Sarvam AI (Mayura model).

Replaces the earlier Google Translate approach — Sarvam is purpose-built
for Indian languages, including natural code-mixed/colloquial output,
which produced noticeably better results in direct testing.

Same function signature as before, so response_engine.py's integration
(translate_to_kannada -> _casualize_kannada) needs no further changes.

Requires:
    pip install sarvamai
And SARVAM_API_KEY set in .env
"""

import os
from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

client = SarvamAI(api_subscription_key=os.getenv("SARVAM_API_KEY"))

# "code-mixed" mode confirmed via testing to produce the best base
# quality — the remaining English-ratio adjustment happens in the
# Groq refinement step (_casualize_kannada) afterward, not here.
MODE = "code-mixed"


def translate_to_kannada(text: str) -> str:
    """
    Translates English text to natural, code-mixed Kannada.
    Returns None on failure — caller must handle that explicitly.
    """
    try:
        response = client.text.translate(
            input=text,
            source_language_code="en-IN",
            target_language_code="kn-IN",
            model="mayura:v1",
            mode=MODE,
        )
        return response.translated_text

    except Exception as e:
        print(f"❌ Sarvam translation error: {e}")
        return None