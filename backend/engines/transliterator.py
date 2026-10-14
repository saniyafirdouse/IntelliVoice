"""
Native script -> Roman letters.

2026-10-13: Kannada now uses a fixed letter-by-letter conversion
(romanize_kannada below) instead of Sarvam's transliteration API. Sarvam's
model rewrote words ("eradu" came out as "do two", Hindi "hain" appeared,
"hostel-n-e"). The rule-based version cannot change words, needs no
network call (faster) and keeps English words exactly as they are.
Set KANNADA_ROMANIZER = "sarvam" to go back to the old behaviour.

(Original notes:) Uses Sarvam AI's transliteration API for other languages.

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
import re

from dotenv import load_dotenv
from sarvamai import SarvamAI

from engines.tts_engine import split_text

load_dotenv()

SOURCE_CODES = {
    "kn": "kn-IN",
    "hi": "hi-IN",
}

KANNADA_ROMANIZER = "rules"   # "rules" (default) or "sarvam"

# ── Rule-based Kannada romanization ─────────────────────────────────────
VIRAMA, NUKTA, ANUSVARA, VISARGA = "್", "಼", "ಂ", "ಃ"
VOWELS = {"ಅ":"a","ಆ":"aa","ಇ":"i","ಈ":"ee","ಉ":"u","ಊ":"oo","ಋ":"ru","ೠ":"roo","ಎ":"e","ಏ":"e","ಐ":"ai","ಒ":"o","ಓ":"o","ಔ":"au"}
SIGNS = {"ಾ":"aa","ಿ":"i","ೀ":"ee","ು":"u","ೂ":"oo","ೃ":"ru","ೄ":"roo","ೆ":"e","ೇ":"e","ೈ":"ai","ೊ":"o","ೋ":"o","ೌ":"au",VIRAMA:""}
CONS = {"ಕ":"k","ಖ":"kh","ಗ":"g","ಘ":"gh","ಙ":"n","ಚ":"ch","ಛ":"chh","ಜ":"j","ಝ":"jh","ಞ":"n",
        "ಟ":"t","ಠ":"th","ಡ":"d","ಢ":"dh","ಣ":"n","ತ":"t","ಥ":"th","ದ":"d","ಧ":"dh","ನ":"n",
        "ಪ":"p","ಫ":"ph","ಬ":"b","ಭ":"bh","ಮ":"m","ಯ":"y","ರ":"r","ಱ":"r","ಲ":"l","ವ":"v",
        "ಶ":"sh","ಷ":"sh","ಸ":"s","ಹ":"h","ಳ":"l","ೞ":"l"}
NUKTA_CONS = {"ಫ":"f","ಜ":"z"}
LABIAL_ETC = set("ಪಫಬಭಮಯರಲವಶಷಸಹಳ")
DIGITS = {chr(0x0CE6+i): str(i) for i in range(10)}
def romanize_kannada(text: str) -> str:
    """Kannada script -> Roman letters, letter by letter (WhatsApp-style spelling)."""
    out=[]; i=0; n=len(text)
    text=text.replace("‌","").replace("‍","")
    n=len(text)
    while i<n:
        c=text[i]
        if c in CONS:
            lat=CONS[c]; j=i+1
            if j<n and text[j]==NUKTA:
                lat=NUKTA_CONS.get(c,lat); j+=1
            if j<n and text[j] in SIGNS:
                out.append(lat+SIGNS[text[j]]); i=j+1
            else:
                out.append(lat+"a"); i=j
            continue
        if c in VOWELS: out.append(VOWELS[c]); i+=1; continue
        if c==ANUSVARA:
            nxt=text[i+1] if i+1<n else ""
            out.append("m" if (nxt in LABIAL_ETC or not nxt.strip() or nxt not in CONS) else "n"); i+=1; continue
        if c==VISARGA: out.append("h"); i+=1; continue
        if c in DIGITS: out.append(DIGITS[c]); i+=1; continue
        if c in ("।","॥"): out.append("."); i+=1; continue
        if c in SIGNS: out.append(SIGNS[c]); i+=1; continue  # stray sign
        out.append(c); i+=1
    s="".join(out)
    # Word-final long "aa" is usually typed short: tumbaa -> tumba, ellaa -> ella.
    s=re.sub(r"\b([a-z]{2,})aa\b", r"\1a", s)
    # Capital letter at the start of each sentence (only if it is a lowercase letter).
    s=re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1)+m.group(2).upper(), s)
    return s


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

    if language == "kn" and KANNADA_ROMANIZER == "rules":
        try:
            return romanize_kannada(text).strip() or None
        except Exception as e:
            print(f"❌ Kannada romanization error: {type(e).__name__}: {e}")
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
