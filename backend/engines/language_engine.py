import asyncio
import io
import json
import os
import re
import tempfile
import threading
import time
import wave

import numpy as np
import py3langid as langid
import whisper                      # used only for whisper.load_audio (reads any format via ffmpeg)
from dotenv import load_dotenv

# The local Whisper model is only a BACKUP for when Groq is unreachable.
# Its library (faster-whisper -> PyAV) contains compiled DLLs that Windows
# security (Smart App Control) can block — seen 2026-10-08:
#   "DLL load failed ... An Application Control policy has blocked this file"
# If it can't load, the server still starts and voice input uses Groq only.
try:
    from faster_whisper import WhisperModel
    _local_whisper_error = None
except Exception as e:                       # ImportError, OSError (blocked DLL), ...
    WhisperModel = None
    _local_whisper_error = f"{type(e).__name__}: {e}"
from groq import Groq

from engines.muril_multitask_classifier import classify_language_emotion_muril

# ── Speech recognition: Whisper via faster-whisper ────────────────────────
# 2026-10-07: switched from openai-whisper "small" (which wrote Kannada
# speech in Hindi script / nonsense) to faster-whisper — the same Whisper
# models, re-implemented for fast CPU inference with int8 quantisation.
# Measured on the project laptop (CPU only, test_kannada.wav):
#   openai-whisper medium, forced kn ............ 12 s
#   faster-whisper medium, int8, forced kn ......  7 s  (best accuracy)
#   faster-whisper small,  int8, forced kn+hint .  3 s  (chosen: good enough, fast)
# Change WHISPER_MODEL_NAME to "medium" for higher accuracy (~7 s).
WHISPER_MODEL_NAME = "small"
WHISPER_COMPUTE_TYPE = "int8"
WHISPER_CPU_THREADS = 4             # 4 measured faster than 6 on the project laptop

# Vocabulary hint: biases Whisper toward the college terms parents use,
# and toward writing Kannada/Hindi in Roman letters, which it does far
# more accurately than native script (and Engines 1–2 handle well).
WHISPER_VOCAB_HINT = (
    "SVIT, CSE, ISE, AIML, KCET, COMEDK, fee, admission, hostel, "
    "scholarship, placement, branch, college"
)
SPEECH_LANGUAGES = ("en", "hi", "kn")

# ── Primary speech recognition: Whisper large-v3-turbo on Groq ───────────
# 2026-10-08: same Whisper family, run on Groq's hardware instead of the
# laptop CPU. Measured on test_kannada.wav: 0.8 s (vs ~3 s local small,
# ~7 s local medium) with comparable accuracy. The local faster-whisper
# model below stays loaded as an automatic BACKUP if Groq is unreachable
# (no internet, outage, rate limit), so voice input never stops working.
# Set USE_GROQ_WHISPER = False to always use the local model.
# Note: "whisper-large-v3" (non-turbo) was rejected — in testing it
# translated Kannada speech into English instead of transcribing it.
load_dotenv()
USE_GROQ_WHISPER = True
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
_groq_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=_groq_key) if _groq_key else None
if USE_GROQ_WHISPER and groq_client is None:
    print("⚠️  GROQ_API_KEY missing — speech recognition will use the local Whisper model only")

whisper_model = None
if WhisperModel is not None:
    try:
        print(f"Loading Whisper model ({WHISPER_MODEL_NAME}, faster-whisper {WHISPER_COMPUTE_TYPE})...")
        whisper_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device="cpu",
            compute_type=WHISPER_COMPUTE_TYPE,
            cpu_threads=WHISPER_CPU_THREADS,
        )
        print("✅ Whisper model loaded (local backup)")
    except Exception as e:
        _local_whisper_error = f"{type(e).__name__}: {e}"
if whisper_model is None:
    print(f"⚠️  Local Whisper backup unavailable ({_local_whisper_error}) — "
          "speech recognition will use Groq only")
    if groq_client is None or not USE_GROQ_WHISPER:
        print("❌ No speech recognition available: Groq is off/unconfigured AND the local model failed")

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


# ── Transcript correction (added 2026-10-08, revised same day) ─────────────
# Real phone recordings showed Whisper mishearing code-mixed speech, e.g.
#   said:  "Ee college alli CSE branch fee eshtu"
#   heard: "E. College LCC branch fee is to"
# ("alli CSE" merged into "LCC"; "eshtu" heard as "is to"). Engine 2 then
# found no branch and the reply talked about an "LCC branch".
#
# How it works (one fast Groq call, ~0.5 s; Whisper itself is unchanged):
#   1. The model returns ONLY a list of fixes: [{"heard": "...", "fixed": "..."}]
#      — never a rewritten sentence.
#   2. The code checks every fix and applies it only if:
#        - "heard" really appears in what Whisper wrote,
#        - "fixed" uses only known college names (from entities.json),
#          common spoken Kannada/Hindi words, or words already in the
#          transcript,
#        - no numbers are involved, and the fix is short.
#      Anything else is rejected — the model cannot add or rewrite.
#   3. On any failure the original transcript is used.
# Whisper's own text is kept in language["stt_raw_text"]; applied and
# rejected fixes are in language["transcript_fixes"] / ["transcript_fixes_rejected"].
# Set TRANSCRIPT_CORRECTION = False to turn it off.
# Previous versions: language_engine_backup_2026-10-08b.py (no corrector),
#                    language_engine_backup_2026-10-08c.py (first corrector),
#                    language_engine_backup_2026-10-08e.py (20B, no sense check).
#
# Revision 3 (after the q1 test turned "Ee" into "ECE"):
#   - uses the larger 120B model and asks it to read the fixed question
#     back and check it makes sense (one branch, natural sentence)
#   - code rejects fixes of a single letter ("E." -> "ECE")
#   - code rejects branch fixes if they would add 2+ different branches
#   - hard limit of 2.5 s, no retries: a slow connection can no longer
#     hold up the reply (13 s was seen) — the original text is used instead
# Revision 4 (2026-10-09; previous: language_engine_backup_2026-10-09b.py):
#   the same recording had "LCC" fixed in only 1 of 4 runs — the prompt
#   now says an unknown capital-letter word in a branch question is a
#   misheard branch and must be changed to the closest-sounding one.
TRANSCRIPT_CORRECTION = True
CORRECTION_MODEL = "openai/gpt-oss-120b"
CORRECTION_TIMEOUT_S = 2.5
MAX_FIXES = 4
MAX_FIX_WORDS = 3

# Everyday words a parent says around college terms (Roman letters).
SPOKEN_WORDS = {
    "kn": ["eshtu", "alli", "ide", "idya", "illa", "beku", "yenu", "enu", "hege",
           "yaavaga", "ge", "ige", "ke", "duddu", "maga", "magalu", "ee", "aa",
           "na", "naa", "gu", "kodi", "heli", "sigutta", "sigutte", "aagutte"],
    "hi": ["kitna", "kitni", "kitne", "kya", "hai", "hain", "kaise", "kab",
           "mein", "ka", "ki", "ke", "ko", "se", "milega", "chahiye"],
}
COLLEGE_WORDS = ["svit", "fee", "fees", "admission", "cutoff", "cut-off", "rank",
                 "seat", "seats", "hostel", "scholarship", "placement", "package",
                 "branch", "college", "semester", "quota", "management",
                 "government", "exam", "course"]


def _load_entities() -> dict:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "database", "seed_data", "entities.json")
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Could not load entities.json for transcript correction: {e}")
        return {}


def _build_vocabulary(entities: dict) -> tuple[str, set]:
    """Returns (names for the prompt, set of allowed lowercase words for fixes)."""
    names = []
    allowed = set(COLLEGE_WORDS)
    for words in SPOKEN_WORDS.values():
        allowed.update(words)
    for group in ("branch", "exam", "quota", "course", "campus_facility"):
        for name, aliases in entities.get(group, {}).items():
            if name == "note":
                continue
            names.append(name)
            allowed.update(_words(name))
            for alias in aliases if isinstance(aliases, list) else []:
                if alias.isascii():
                    allowed.update(_words(alias))
    if not names:
        names = ["CSE", "ISE", "AIML", "KCET", "COMEDK"]
        allowed.update(n.lower() for n in names)
    return ", ".join(dict.fromkeys(names)), allowed


def _words(text: str) -> list:
    """Lowercase words, keeping things like 'CSE-AIML' and 'B.E.' together."""
    return [w.strip(".-") for w in re.findall(r"[\w][\w.\-]*", text.lower()) if w.strip(".-")]


def _build_branch_phrases(entities: dict) -> dict:
    """lowercase name/alias -> branch key, e.g. 'computer science' -> 'CSE'."""
    phrases = {}
    for key, aliases in entities.get("branch", {}).items():
        if key == "note":
            continue
        phrases[key.lower()] = key
        for alias in aliases if isinstance(aliases, list) else []:
            if alias.isascii():
                phrases[alias.lower()] = key
    return phrases


def _branches_in(text: str) -> set:
    lower = text.lower()
    return {key for phrase, key in BRANCH_PHRASES.items()
            if re.search(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", lower)}


_ENTITIES = _load_entities()
KNOWN_TERMS, ALLOWED_FIX_WORDS = _build_vocabulary(_ENTITIES)
BRANCH_PHRASES = _build_branch_phrases(_ENTITIES)

TRANSCRIPT_CORRECTION_PROMPT = """A parent asked SVIT college's admissions assistant a question by voice. A speech recognizer wrote it down, but it sometimes mishears college terms and Kannada/Hindi words and writes similar-sounding English words instead.
The parent spoke {language_name}, often mixed with English words.

Known college terms: SVIT, {known_terms}, fee, fees, admission, cutoff, rank, seat, hostel, scholarship, placement, package, branch, college, semester, quota.
Common spoken words:
Kannada - eshtu (how much), alli (in), ide (is there), illa (no), beku (want), yenu (what), hege (how), yaavaga (when), ge (to), duddu (money), maga (son), magalu (daughter), ee (this).
Hindi - kitna, kitni, kya, hai, kaise, kab, mein, ka, ki, ke, ko, se.

How mishearing happens:
- A word is replaced by a similar-sounding English word or name: "eshtu" -> "Esther" or "is to".
- A term is split into pieces: "KCET" -> "Kay CET".
- A Kannada word and a college term next to it are MERGED into one wrong word: "alli ISE" -> "LIC".
In a {language_name} question, an English-looking word that makes no sense where it stands is almost always one of these mistakes.
"E." or "Ee" or "Yee" at the start of a Kannada question is usually the word "ee" (this) — NOT a branch name.
A short CAPITAL-LETTER word that is NOT one of the known terms (for example "ACML", "ISC", "LIC") is almost always a misheard known term, often merged with the Kannada word before it. If the question is about a branch (fee, cutoff, seat, placement) and no known branch name is in it, change that word to the closest-sounding known branch — do not leave an unknown abbreviation in place.

Your job: list ONLY the mistakes. For each, give the exact wrong text as it appears ("heard") and what the parent most likely said ("fixed"), using only the known terms and spoken words above.
- Do NOT rewrite the sentence, translate, fix grammar, or add anything.
- Never change numbers or names that are not in the lists above.
- If you are not confident about a word, leave it out. If nothing is wrong, return an empty list.

BEFORE ANSWERING, CHECK THE WHOLE QUESTION:
Apply your fixes in your head and read the full fixed question. It must be a natural question a parent would really ask.
- A parent normally asks about ONE branch. If your fixes would put two different branch names into the question (e.g. "ee ECE college alli CSE fees"), that is wrong — keep only the fix that fits the sentence best.
- If a fix makes the question less natural or less logical, drop that fix.

Example:
Text: hostel fee Esther, Kay CET alli seat ide?
Answer: {{"fixes": [{{"heard": "Esther", "fixed": "eshtu"}}, {{"heard": "Kay CET", "fixed": "KCET"}}]}}

Example:
Text: ACML branch cutoff Esther?
Answer: {{"fixes": [{{"heard": "ACML", "fixed": "AIML"}}, {{"heard": "Esther", "fixed": "eshtu"}}]}}

Example:
Text: What is the hostel fee for girls?
Answer: {{"fixes": []}}

Return ONLY JSON in exactly this form: {{"fixes": [{{"heard": "...", "fixed": "..."}}]}}

Text: {text}
Answer:"""


def _parse_fixes(content: str) -> list:
    """Pulls the fixes list out of the model's answer; [] if it isn't valid JSON."""
    content = (content or "").strip()
    first, last = content.find("{"), content.rfind("}")
    if first == -1 or last <= first:
        return []
    try:
        data = json.loads(content[first:last + 1])
    except json.JSONDecodeError:
        return []
    fixes = data.get("fixes", []) if isinstance(data, dict) else []
    return [f for f in fixes if isinstance(f, dict)][:MAX_FIXES]


def _check_fix(fix: dict, text: str) -> tuple[re.Pattern | None, str, str]:
    """Returns (pattern to replace, replacement, reason). pattern is None if rejected."""
    heard = str(fix.get("heard", "")).strip()
    fixed = str(fix.get("fixed", "")).strip()
    if not heard or not fixed:
        return None, fixed, "empty"
    if heard.lower() == fixed.lower():
        return None, fixed, "no change"
    if any(ch.isdigit() for ch in heard + fixed):
        return None, fixed, "involves a number"
    if sum(ch.isalpha() for ch in heard) < 2:
        return None, fixed, "single letter - too little to trust"
    fixed_words = _words(fixed)
    if not fixed_words or len(fixed_words) > MAX_FIX_WORDS or len(_words(heard)) > MAX_FIX_WORDS:
        return None, fixed, "too long"
    transcript_words = set(_words(text))
    unknown = [w for w in fixed_words if w not in ALLOWED_FIX_WORDS and w not in transcript_words]
    if unknown:
        return None, fixed, f"unknown words {unknown}"
    pattern = re.compile(rf"(?<!\w){re.escape(heard)}(?!\w)", re.IGNORECASE)
    if not pattern.search(text):
        return None, fixed, "not in transcript"
    return pattern, fixed, "ok"


def _correct_transcript_sync(text: str, language: str | None) -> dict:
    """Returns {"text", "corrected", "fixes", "rejected", "correction_ms"}. Never raises."""
    started = time.perf_counter()
    result = {"text": text, "corrected": False, "fixes": [], "rejected": [], "correction_ms": 0}
    if not (TRANSCRIPT_CORRECTION and groq_client is not None and text.strip()):
        return result
    try:
        language_name = LANGUAGE_MAP.get(language, "Kannada, Hindi or English")
        response = groq_client.with_options(
            timeout=CORRECTION_TIMEOUT_S, max_retries=0,   # never hold up the reply
        ).chat.completions.create(
            model=CORRECTION_MODEL,
            messages=[{"role": "user", "content": TRANSCRIPT_CORRECTION_PROMPT.format(
                language_name=language_name, known_terms=KNOWN_TERMS, text=text,
            )}],
            temperature=0,
            max_tokens=800,            # reasoning model: room to think + answer
            reasoning_effort="low",
        )
        # 1. Check each fix on its own.
        accepted = []
        for fix in _parse_fixes(response.choices[0].message.content):
            entry = {"heard": fix.get("heard"), "fixed": fix.get("fixed")}
            pattern, fixed, reason = _check_fix(fix, text)
            if pattern is None:
                result["rejected"].append({**entry, "reason": reason})
            else:
                accepted.append((entry, fixed))

        # 2. Never let fixes put two different branches into the question —
        #    a wrong branch means a wrong fee. Better to fix no branch at all.
        already = _branches_in(text)
        added = {id(e): _branches_in(f) - already for e, f in accepted}
        all_added = set().union(*added.values()) if added else set()
        if len(all_added) >= 2:
            kept = []
            for entry, fixed in accepted:
                if added[id(entry)]:
                    result["rejected"].append({**entry, "reason": f"would add 2+ branches {sorted(all_added)}"})
                else:
                    kept.append((entry, fixed))
            accepted = kept

        # 3. Apply what is left.
        corrected = text
        for entry, fixed in accepted:
            pattern = re.compile(rf"(?<!\w){re.escape(str(entry['heard']).strip())}(?!\w)", re.IGNORECASE)
            if not pattern.search(corrected):
                result["rejected"].append({**entry, "reason": "overlaps another fix"})
                continue
            corrected = pattern.sub(fixed, corrected, count=1)
            result["fixes"].append(entry)
        result["text"] = corrected
        result["corrected"] = corrected != text
    except Exception as e:
        print(f"⚠️  Transcript correction skipped ({type(e).__name__}: {e})")
    result["correction_ms"] = int((time.perf_counter() - started) * 1000)
    return result


# ── Transcribe audio → text ────────────────────────────────────────────────
def _pick_speech_language(audio, language: str | None) -> tuple[str | None, str, float | None]:
    """
    Decides which language Whisper should transcribe in.
    Returns (language, source, confidence).
      - If the user picked a language (frontend sends en/hi/kn), use it.
        This is the reliable, fast path (~3 s total).
      - Otherwise ask Whisper to guess, limited to en/hi/kn. Slower (one
        extra pass) and less reliable for Kannada with the small model.
    """
    if language in SPEECH_LANGUAGES:
        return language, "user_selected", None
    try:
        _, _, all_probs = whisper_model.detect_language(audio)
        probs = dict(all_probs)
        best = max(SPEECH_LANGUAGES, key=lambda l: probs.get(l, 0.0))
        return best, "auto_detected", round(float(probs.get(best, 0.0)), 2)
    except Exception as e:
        print(f"⚠️  Whisper language detection failed, letting Whisper decide: {e}")
        return None, "whisper_default", None


# 2026-10-14: Whisper sometimes hears Hindi / Hinglish as "Urdu" and writes the
# question in Urdu (Arabic) script ("ہائیر سٹڈیز کے لیے...") — spoken Hindi and
# Urdu sound almost the same. IntelliVoice only supports en / hi / kn, so any
# Urdu-script transcript is transcribed again as Hindi (Devanagari script).
_URDU_SCRIPT = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")


def _is_urdu_script(text: str) -> bool:
    """True when most letters are Arabic/Urdu script."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    return sum(1 for ch in letters if _URDU_SCRIPT.match(ch)) / len(letters) > 0.3


def _transcribe_groq(audio_bytes: bytes, filename: str, language: str | None) -> dict:
    """Primary path: Whisper large-v3-turbo on Groq. Raises on any failure."""
    kwargs = {
        "file": (filename or "audio.wav", audio_bytes),
        "model": GROQ_WHISPER_MODEL,
        "prompt": WHISPER_VOCAB_HINT,
        "temperature": 0,
    }
    if language in SPEECH_LANGUAGES:
        kwargs["language"] = language
    result = groq_client.audio.transcriptions.create(**kwargs)
    text = (result.text or "").strip()
    if _is_urdu_script(text):
        # Heard as Urdu: transcribe again as Hindi so the question is in Devanagari.
        print("ℹ️  Whisper wrote Urdu script — transcribing again as Hindi")
        retry = groq_client.audio.transcriptions.create(**{**kwargs, "language": "hi"})
        retry_text = (retry.text or "").strip()
        if retry_text and not _is_urdu_script(retry_text):
            return {
                "raw_text": retry_text,
                "speech_language": "hi",
                "speech_language_source": "auto_detected",
                "speech_language_confidence": None,
                "stt_engine": f"groq:{GROQ_WHISPER_MODEL}",
            }
    return {
        "raw_text": text,
        "speech_language": language if language in SPEECH_LANGUAGES else None,
        "speech_language_source": "user_selected" if language in SPEECH_LANGUAGES else "auto_detected",
        "speech_language_confidence": None,
        "stt_engine": f"groq:{GROQ_WHISPER_MODEL}",
    }


def _transcribe_local(audio_bytes: bytes, filename: str, language: str | None) -> dict:
    """Backup path: local faster-whisper on the CPU (slower, works offline)."""
    if whisper_model is None:
        raise RuntimeError(f"Local Whisper backup is unavailable ({_local_whisper_error})")
    suffix = os.path.splitext(filename or "")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        # whisper.load_audio decodes any format with ffmpeg to 16 kHz mono.
        # (faster-whisper's own file reader breaks with PyAV 19, so it is
        # given the decoded audio directly.)
        audio = whisper.load_audio(tmp_path)
    finally:
        os.unlink(tmp_path)

    speech_language, source, confidence = _pick_speech_language(audio, language)
    segments, _info = whisper_model.transcribe(
        audio,
        language=speech_language,
        initial_prompt=WHISPER_VOCAB_HINT,
        beam_size=1,
        without_timestamps=True,
        condition_on_previous_text=False,
    )
    raw_text = " ".join(seg.text.strip() for seg in segments).strip()
    return {
        "raw_text": raw_text,
        "speech_language": speech_language,
        "speech_language_source": source,
        "speech_language_confidence": confidence,
        "stt_engine": f"local:faster-whisper-{WHISPER_MODEL_NAME}",
    }


# ── Kannada speech recognition: Sarvam (added 2026-10-12) ─────────────────
# Live tests from the browser showed Whisper mishearing mixed Kannada-English
# badly ("e college alli CSE ge fees eshtu" -> "college CSE KCET STO").
# English and Hindi were fine. For questions where the user chose KANNADA,
# Sarvam's Indian-language speech model is used first; Whisper (Groq, then
# local) stays the automatic backup, and is still used for English, Hindi
# and "auto-detect".
#   saaras:v4, mode "translit" = Kannada speech written in English letters
#   ("CSE fee eshtu"), the same style Engine 2 and the corrector expect.
#   keyterms = college names it should listen for (saaras:v4 only).
# Set KANNADA_STT = "whisper" to go back to Whisper only.
# Docs: docs.sarvam.ai -> Speech-to-Text (REST API, output modes).
# Previous version of this file: language_engine_backup_2026-10-12.py
KANNADA_STT = "sarvam"                      # "sarvam" | "whisper"
SARVAM_STT_MODELS = ("saaras:v4", "saaras:v3")
SARVAM_STT_MODE = "translit"
SARVAM_MAX_SECONDS = 30                     # Sarvam's limit per request
_EXTRA_KEYTERMS = ["SVIT", "KCET", "COMEDK", "CSE", "ISE", "ECE", "AIML", "fee", "fees",
                   "hostel", "cutoff", "placement", "scholarship", "admission",
                   "eshtu", "alli", "beku", "ide"]


def _sarvam_keyterms() -> list:
    terms = [t.strip() for t in KNOWN_TERMS.split(",")] + _EXTRA_KEYTERMS
    unique = []
    for t in terms:
        if t and len(t) <= 64 and t.lower() not in {u.lower() for u in unique}:
            unique.append(t)
    return unique[:50]


def _to_wav_16k(audio_bytes: bytes, filename: str) -> bytes:
    """Any recording (webm from the browser, m4a/mp4 from a phone) -> 16 kHz mono WAV."""
    suffix = os.path.splitext(filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        audio = whisper.load_audio(tmp_path)        # ffmpeg -> float32, 16 kHz mono
    finally:
        os.unlink(tmp_path)
    audio = audio[: 16000 * SARVAM_MAX_SECONDS]
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(pcm)
    return out.getvalue()


def _transcribe_sarvam(audio_bytes: bytes, filename: str, language: str | None) -> dict:
    """Sarvam speech-to-text for Kannada. Raises on any failure (caller falls back)."""
    from engines.tts_engine import _get_client      # same Sarvam client/key as the voice
    client = _get_client()
    wav = _to_wav_16k(audio_bytes, filename)
    last_error = None
    for model in SARVAM_STT_MODELS:
        attempts = [{"model": model, "language_code": "kn-IN", "mode": SARVAM_STT_MODE}]
        if model == "saaras:v4":
            attempts.insert(0, {**attempts[0], "keyterms": _sarvam_keyterms()})
        for kwargs in attempts:
            try:
                response = client.speech_to_text.transcribe(file=("audio.wav", wav, "audio/wav"), **kwargs)
            except TypeError as e:           # older sarvamai without this parameter
                last_error = e
                continue
            except Exception as e:           # e.g. model not available: try the next model
                last_error = e
                break
            text = (getattr(response, "transcript", "") or "").strip()
            if not text:
                raise RuntimeError("Sarvam returned an empty transcript")
            return {
                "raw_text": text,
                "speech_language": "kn",
                "speech_language_source": "user_selected",
                "speech_language_confidence": None,
                "stt_engine": f"sarvam:{model}:{SARVAM_STT_MODE}" + (" +keyterms" if "keyterms" in kwargs else ""),
            }
    raise RuntimeError(f"Sarvam speech-to-text failed: {type(last_error).__name__}: {last_error}")


def _transcribe_sync(audio_bytes: bytes, filename: str, language: str | None) -> dict:
    """Kannada: Sarvam first. Then Groq Whisper; on any problem, the local model."""
    started = time.perf_counter()
    if language == "kn" and KANNADA_STT == "sarvam":
        try:
            stt = _transcribe_sarvam(audio_bytes, filename, language)
            stt["stt_ms"] = int((time.perf_counter() - started) * 1000)
            return stt
        except Exception as e:
            print(f"⚠️  Sarvam speech-to-text failed ({type(e).__name__}: {e}) — using Whisper")
    if USE_GROQ_WHISPER and groq_client is not None:
        try:
            stt = _transcribe_groq(audio_bytes, filename, language)
            stt["stt_ms"] = int((time.perf_counter() - started) * 1000)
            return stt
        except Exception as e:
            print(f"⚠️  Groq Whisper failed ({type(e).__name__}: {e}) — using local Whisper")
    stt = _transcribe_local(audio_bytes, filename, language)
    stt["stt_ms"] = int((time.perf_counter() - started) * 1000)
    return stt


# 2026-10-09 (speed): the steps are also available separately, so the
# voice route can start understanding the question (Engines 2+3) on
# Whisper's text WHILE the corrector runs, and reuse that work when the
# corrector finds nothing to fix. transcribe_audio() still does all the
# steps in order, exactly as before (used by tests/test_pipeline.py).
# Previous version: language_engine_backup_2026-10-09-speed.py

async def speech_to_text(audio_bytes: bytes, filename: str = "audio.wav",
                         language: str | None = None) -> dict:
    """Whisper only (Groq, local backup). Raises if both fail."""
    return await asyncio.to_thread(_transcribe_sync, audio_bytes, filename, language)


async def correct_transcript(text: str, speech_language: str | None) -> dict:
    """The transcript corrector. Never raises."""
    return await asyncio.to_thread(_correct_transcript_sync, text, speech_language)


def no_correction(text: str) -> dict:
    """A 'nothing fixed' result, used while the real corrector is still running."""
    return {"text": text, "corrected": False, "fixes": [], "rejected": [], "correction_ms": 0}


def set_correction_info(lang_info: dict, correction: dict) -> None:
    lang_info["transcript_corrected"] = correction["corrected"]
    lang_info["correction_ms"] = correction["correction_ms"]
    lang_info["transcript_fixes"] = correction["fixes"]
    lang_info["transcript_fixes_rejected"] = correction["rejected"]


async def build_language_result(stt: dict, correction: dict) -> dict:
    """Language detection (MuRIL) on the (corrected) text + all speech details."""
    raw_text = correction["text"]

    lang_info = await detect_language(raw_text)
    lang_info["text_detected_primary"] = lang_info["primary"]
    if stt["speech_language_source"] == "user_selected":
        # The user's explicit choice decides the reply language.
        lang_info["primary"] = stt["speech_language"]
        lang_info["primary_name"] = LANGUAGE_MAP[stt["speech_language"]]
        lang_info["is_code_switched"] = (
            lang_info["primary"] in {"hi", "kn"} and lang_info.get("has_latin", False)
        )
    lang_info["speech_language"] = stt["speech_language"]
    lang_info["speech_language_source"] = stt["speech_language_source"]
    lang_info["speech_language_confidence"] = stt["speech_language_confidence"]
    lang_info["stt_engine"] = stt["stt_engine"]
    lang_info["stt_ms"] = stt["stt_ms"]
    lang_info["stt_raw_text"] = stt["raw_text"]          # exactly what Whisper heard
    set_correction_info(lang_info, correction)

    return {
        "success": True,
        "raw_text": raw_text,
        "normalized_text": normalize_text(raw_text),
        "language": lang_info
    }


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav",
                           language: str | None = None) -> dict:
    """
    All steps in order: Whisper -> corrector -> language detection.
    language: optional "en" / "hi" / "kn" chosen by the user in the app.
              Strongly recommended — skips a slow and less reliable guess.
    """
    try:
        stt = await speech_to_text(audio_bytes, filename, language)
        correction = await correct_transcript(stt["raw_text"], stt["speech_language"])
        return await build_language_result(stt, correction)

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


# ── Warm-up at server start ───────────────────────────────────────────────
# The first MuRIL prediction (loads ~900 MB of weights) and the first local
# Whisper run are several seconds slower than later ones. Doing one tiny
# run of each at startup means the first parent's question is not slower.
def _warm_up():
    started = time.perf_counter()
    try:
        if whisper_model is None:
            raise RuntimeError("local model not loaded")
        silence = np.zeros(16000, dtype=np.float32)          # 1 s of silence
        list(whisper_model.transcribe(silence, language="en", beam_size=1,
                                      without_timestamps=True)[0])
    except Exception as e:
        print(f"⚠️  Whisper warm-up skipped: {e}")
    try:
        # MuRIL's function is async; run it on its own event loop in a
        # helper thread so this works even while the server's loop is starting.
        t = threading.Thread(target=lambda: asyncio.run(
            classify_language_emotion_muril("CSE fee eshtu")))
        t.start()
        t.join()
    except Exception as e:
        print(f"⚠️  MuRIL warm-up skipped: {e}")
    print(f"✅ Speech + language models warmed up ({time.perf_counter() - started:.1f}s)")


_warm_up()
