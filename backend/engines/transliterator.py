"""
Native script -> Roman letters, using Sarvam AI's transliteration API.

Used by Engine 5 ONLY for on-screen display when the user chooses
romanized output for Kannada. The native-script text is still what
gets spoken by TTS (Bulbul pronounces native script correctly; it can
mispronounce romanized Kannada).

English words already written in Roman letters inside the Kannada
text (CSE, KCET, fee, college...) pass through unchanged.

Requires:
    pip install sarvamai
And SARVAM_API_KEY set in .env
"""

import os

from dotenv import load_dotenv
from sarvamai import SarvamAI

from engines.tts_engine import split_text

load_dotenv()

SOURCE_CODES = {
    "kn": "kn-IN",
    "hi": "hi-IN",
}

# Sarvam's transliteration endpoint has a smaller input limit than TTS.
MAX_CHARS_PER_REQUEST = 900

_client = None


def _get_client() -> SarvamAI:
    global _client
    if _client is None:
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise RuntimeError("SARVAM_API_KEY is not set in .env")
        _client = SarvamAI(api_subscription_key=api_key)
    return _client


def romanize(text: str, language: str) -> str | None:
    """
    Converts Kannada (or Hindi) script text to Roman letters.
    Returns None on failure — caller falls back to the native text.
    Synchronous; Engine 5 calls it via asyncio.to_thread.
    """
    source_code = SOURCE_CODES.get(language)
    if not source_code or not text or not text.strip():
        return None

    try:
        client = _get_client()
        parts = []
        for chunk in split_text(text, MAX_CHARS_PER_REQUEST):
            response = client.text.transliterate(
                input=chunk,
                source_language_code=source_code,
                target_language_code="en-IN",
            )
            parts.append(response.transliterated_text)
        result = " ".join(p.strip() for p in parts if p).strip()
        return result or None

    except Exception as e:
        print(f"❌ Sarvam transliteration error ({source_code}): {type(e).__name__}: {e}")
        return None
