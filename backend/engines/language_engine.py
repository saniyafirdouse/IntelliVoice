import whisper
import tempfile
import os
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Makes language detection consistent across runs
DetectorFactory.seed = 0

# Load Whisper model once when engine starts
# "base" model is fast and accurate enough for our use case
# With 16GB RAM you can use "small" for better accuracy
print("Loading Whisper model...")
whisper_model = whisper.load_model("small")
print("✅ Whisper model loaded")


# ── Language code mapping ──────────────────────────────────────────────────
LANGUAGE_MAP = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "te": "Telugu",
    "ta": "Tamil",
    "mr": "Marathi"
}

# Kannada and Hindi script character ranges for script detection
KANNADA_RANGE = range(0x0C80, 0x0CFF)
DEVANAGARI_RANGE = range(0x0900, 0x097F)


# ── Script-based language detection (more reliable than langdetect for Indian scripts)
def detect_script(text: str) -> str | None:
    kannada_count = sum(1 for ch in text if ord(ch) in KANNADA_RANGE)
    devanagari_count = sum(1 for ch in text if ord(ch) in DEVANAGARI_RANGE)
    total = len(text.strip())

    if total == 0:
        return None

    if kannada_count / total > 0.2:
        return "kn"
    if devanagari_count / total > 0.2:
        return "hi"
    return None


# ── Detect language of transcribed text ───────────────────────────────────
def detect_language(text: str) -> dict:
    if not text or not text.strip():
        return {"primary": "en", "primary_name": "English", "is_code_switched": False}

    # First try script-based detection (most reliable for Indian scripts)
    script_lang = detect_script(text)

    # Then try langdetect
    try:
        detected = detect(text)
    except LangDetectException:
        detected = "en"

    # Determine primary language
    primary = script_lang if script_lang else detected

    # Check for code-switching: text has both Latin and Indian script characters
    has_latin = any(ch.isascii() and ch.isalpha() for ch in text)
    has_kannada = any(ord(ch) in KANNADA_RANGE for ch in text)
    has_devanagari = any(ord(ch) in DEVANAGARI_RANGE for ch in text)
    is_code_switched = has_latin and (has_kannada or has_devanagari)

    return {
        "primary": primary,
        "primary_name": LANGUAGE_MAP.get(primary, "English"),
        "is_code_switched": is_code_switched,
        "has_kannada": has_kannada,
        "has_devanagari": has_devanagari,
        "has_latin": has_latin
    }


# ── Normalize code-switched text ──────────────────────────────────────────
# Cleans up common code-switch patterns for better intent matching
def normalize_text(text: str) -> str:
    if not text:
        return ""

    # Common code-switch normalizations for SVIT context
    replacements = {
        "kitna hai": "how much",
        "kitni hai": "how much",
        "kya hai": "what is",
        "batao": "tell me",
        "bhaiya": "",
        "bhai": "",
        "yaar": "",
        "please": "",
        "eshtu": "how much",
        "enu": "what",
        "hege": "how",
        "yaaru": "who",
        "eega": "now",
        "ide": "is available",
        "illa": "is not available",
    }

    normalized = text.lower().strip()
    for pattern, replacement in replacements.items():
        normalized = normalized.replace(pattern, replacement)

    # Remove extra spaces
    normalized = " ".join(normalized.split())
    return normalized


# ── Main STT function: audio file → text ──────────────────────────────────
async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> dict:
    try:
        # Save audio bytes to a temporary file
        # Whisper needs a file path, not raw bytes
        with tempfile.NamedTemporaryFile(
            suffix=os.path.splitext(filename)[1] or ".wav",
            delete=False
        ) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        # Transcribe using Whisper
        # task="transcribe" keeps original language
        # task="translate" would convert to English (we don't want that)
        result = whisper_model.transcribe(
            tmp_path,
            task="transcribe",
            language=None  # Auto-detect language
        )

        raw_text = result["text"].strip()
        whisper_language = result.get("language", "en")

        # Clean up temp file
        os.unlink(tmp_path)

        # Detect language from transcribed text
        lang_info = detect_language(raw_text)

        # If Whisper detected a language and our detector didn't find Indian script,
        # trust Whisper's detection
        if not lang_info["has_kannada"] and not lang_info["has_devanagari"]:
            lang_info["primary"] = whisper_language
            lang_info["primary_name"] = LANGUAGE_MAP.get(whisper_language, "English")

        # Normalize the text
        normalized_text = normalize_text(raw_text)

        return {
            "success": True,
            "raw_text": raw_text,
            "normalized_text": normalized_text,
            "language": lang_info,
            "whisper_detected_language": whisper_language
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "raw_text": "",
            "normalized_text": "",
            "language": {
                "primary": "en",
                "primary_name": "English",
                "is_code_switched": False
            }
        }


# ── Process text input directly (no audio) ────────────────────────────────
# For when user types instead of speaking
async def process_text_input(text: str) -> dict:
    if not text or not text.strip():
        return {
            "success": False,
            "error": "Empty text provided",
            "raw_text": "",
            "normalized_text": "",
            "language": {
                "primary": "en",
                "primary_name": "English",
                "is_code_switched": False
            }
        }

    lang_info = detect_language(text)
    normalized_text = normalize_text(text)

    return {
        "success": True,
        "raw_text": text,
        "normalized_text": normalized_text,
        "language": lang_info,
        "whisper_detected_language": None
    }