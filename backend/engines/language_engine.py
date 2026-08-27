import whisper
import tempfile
import os
import py3langid as langid
from engines.muril_multitask_classifier import classify_language_emotion_muril

print("Loading Whisper model...")
whisper_model = whisper.load_model("small")
print("✅ Whisper model loaded")

# Restrict py3langid's candidate languages to exactly our 3 supported ones.
# This is the key fix — instead of letting it choose from 97 languages
# (which is how we got Finnish/Danish/Norwegian on short romanized text),
# it can now only ever return en, hi, or kn.
langid.set_languages(["en", "hi", "kn"])
print("✅ py3langid loaded, restricted to en/hi/kn")

# ── Supported languages ────────────────────────────────────────────────────
LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada"
}
SUPPORTED_LANGUAGES = set(LANGUAGE_MAP.keys())

# Script character ranges — used for 100% accurate detection when native
# script is present, which always wins over any statistical guess.
KANNADA_RANGE = range(0x0C80, 0x0CFF)
DEVANAGARI_RANGE = range(0x0900, 0x097F)


# ── Script-based detection ─────────────────────────────────────────────────
def detect_script(text: str) -> str | None:
    total = max(len(text.strip()), 1)
    kn_count = sum(1 for ch in text if ord(ch) in KANNADA_RANGE)
    hi_count = sum(1 for ch in text if ord(ch) in DEVANAGARI_RANGE)
    if kn_count / total > 0.15:
        return "kn"
    if hi_count / total > 0.15:
        return "hi"
    return None


# ── Fallback: original py3langid detection (kept for safety) ──────────────
def detect_language_py3langid(text: str) -> dict:
    if not text or not text.strip():
        return {
            "primary": "en",
            "primary_name": "English",
            "is_code_switched": False
        }

    script_lang = detect_script(text)

    try:
        detected_lang, confidence = langid.classify(text)
    except Exception:
        detected_lang, confidence = "en", 0.0

    primary = script_lang if script_lang else detected_lang

    if primary not in SUPPORTED_LANGUAGES:
        primary = "en"

    has_latin = any(ch.isascii() and ch.isalpha() for ch in text)
    has_kannada = any(ord(ch) in KANNADA_RANGE for ch in text)
    has_devanagari = any(ord(ch) in DEVANAGARI_RANGE for ch in text)

    is_code_switched = (primary in {"hi", "kn"}) and has_latin

    return {
        "primary": primary,
        "primary_name": LANGUAGE_MAP.get(primary, "English"),
        "is_code_switched": is_code_switched,
        "has_kannada": has_kannada,
        "has_devanagari": has_devanagari,
        "has_latin": has_latin,
        "confidence": round(float(confidence), 2)
    }


# ── Main language detection — fine-tuned MuRIL, empirically validated ─────
# 95% vs py3langid's 80% on held-out test data (see database/seed_data/
# muril_training/ evaluation results). Falls back to py3langid only if
# MuRIL fails to load or errors at runtime.
async def detect_language(text: str) -> dict:
    if not text or not text.strip():
        return {
            "primary": "en",
            "primary_name": "English",
            "is_code_switched": False
        }

    muril_result = await classify_language_emotion_muril(text)

    if muril_result["success"]:
        primary = muril_result["language"]
        confidence = muril_result["language_confidence"]
    else:
        fallback = detect_language_py3langid(text)
        primary = fallback["primary"]
        confidence = fallback.get("confidence")

    has_latin = any(ch.isascii() and ch.isalpha() for ch in text)
    has_kannada = any(ord(ch) in KANNADA_RANGE for ch in text)
    has_devanagari = any(ord(ch) in DEVANAGARI_RANGE for ch in text)

    is_code_switched = (primary in {"hi", "kn"}) and has_latin

    return {
        "primary": primary,
        "primary_name": LANGUAGE_MAP.get(primary, "English"),
        "is_code_switched": is_code_switched,
        "has_kannada": has_kannada,
        "has_devanagari": has_devanagari,
        "has_latin": has_latin,
        "confidence": confidence
    }


# ── Normalize text ─────────────────────────────────────────────────────────
# Kept intentionally simple. Meaning-level understanding is Engine 2's job
# (Sentence Transformers), not string replacement here — hardcoded phrase
# substitution was removed as it added false confidence without real
# generalization.
def normalize_text(text: str) -> str:
    if not text:
        return ""
    return " ".join(text.lower().strip().split())


# ── Transcribe audio → text ────────────────────────────────────────────────
async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    try:
        suffix = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        result = whisper_model.transcribe(tmp_path, task="transcribe", language=None)
        raw_text = result["text"].strip()
        os.unlink(tmp_path)

        lang_info = await detect_language(raw_text)
        normalized = normalize_text(raw_text)

        return {
            "success": True,
            "raw_text": raw_text,
            "normalized_text": normalized,
            "language": lang_info
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "raw_text": "",
            "normalized_text": "",
            "language": {"primary": "en", "primary_name": "English", "is_code_switched": False}
        }


# ── Process text input directly ────────────────────────────────────────────
async def process_text_input(text: str) -> dict:
    if not text or not text.strip():
        return {
            "success": False,
            "error": "Empty text",
            "raw_text": "",
            "normalized_text": "",
            "language": {"primary": "en", "primary_name": "English", "is_code_switched": False}
        }

    lang_info = await detect_language(text)
    normalized = normalize_text(text)

    return {
        "success": True,
        "raw_text": text,
        "normalized_text": normalized,
        "language": lang_info
    }