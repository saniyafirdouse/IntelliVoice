"""
Text-to-Speech — Sarvam AI Bulbul v3.

Used by Engine 5 (response_engine.py) to turn the final response text
into speech. Always called with the NATIVE-script text for Kannada
(Kannada script), since that is what Bulbul pronounces correctly —
the romanized version is for on-screen display only.

Returns base64-encoded WAV so the API route can send it straight to
the frontend in JSON (frontend plays it with an <audio> tag or
new Audio("data:audio/wav;base64," + audio_base64)).

Requires:
    pip install sarvamai
And SARVAM_API_KEY set in .env
"""

import array
import base64
import io
import os
import re
import threading
import wave
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv()

TTS_MODEL = "bulbul:v3"

LANGUAGE_CODES = {
    "en": "en-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
}

# Voices chosen by the team (2026-10-06): Ritu for English,
# Simran for Hindi, Roopa for Kannada. Change here to try others.
SPEAKERS = {
    "en": "ritu",
    "hi": "simran",
    "kn": "roopa",
}

# Speaking speed per language. 1.0 is Sarvam's default (felt too slow
# on a phone call). Kannada's 1.2 was tuned for Neha; adjust if Roopa
# sounds too fast in Kannada.
PACE = {
    "en": 1.1,
    "hi": 1.1,
    "kn": 1.1,      # 1.3 made Neha swallow syllables (e.g. ಆಗ್ತಿದ್ದೀರಿ)
}

# Abbreviations the voice model reads as a word instead of letters
# (e.g. "SVIT" spoken as one word). Replaced ONLY in the text sent to
# TTS — the on-screen text keeps the normal abbreviation.
# Kannada/Hindi use letter names in their own script, which Bulbul
# pronounces more reliably than Latin letters inside native text.
# Add more entries here if other abbreviations sound wrong.
SPOKEN_FORMS = {
    "SVIT": {
        "en": "S V I T",
        "kn": "ಎಸ್ ವಿ ಐ ಟಿ",
        "hi": "एस वी आई टी",
    },
    "CSE": {                     # was heard as "CAC"
        "en": "C S E",
        "kn": "ಸಿ ಎಸ್ ಇ",
        "hi": "सी एस ई",
    },
    "COMEDK": {                  # was heard as "committee"
        "en": "Comed K",
        "kn": "ಕಾಮೆಡ್ ಕೆ",
        "hi": "कॉमेड के",
    },
    "KCET": {                    # was heard as "KET"
        "en": "K C E T",
        "kn": "ಕೆ ಸಿ ಇ ಟಿ",
        "hi": "के सी ई टी",
    },
}

# Word for "rupees" when a ₹ amount is spoken in native-script text.
RUPEE_WORDS = {
    "en": "rupees",
    "kn": "ರೂಪಾಯಿ",
    "hi": "रुपये",
}

# Text is sent to TTS roughly one sentence at a time (short sentences
# are packed together up to this size). Long single requests were
# getting their endings dropped by Bulbul (case 5, case 7); short
# requests avoid that, and the audio pieces are joined back together.
MAX_CHARS_PER_REQUEST = 250

# Sentence pieces are converted in parallel so splitting doesn't make
# the reply slower.
MAX_PARALLEL_REQUESTS = 6

# 2026-10-09 (speed): the voice takes roughly as long as the text is long,
# and a 150-character reply went as ONE request (~4 s). Now every sentence
# is its own request, all made at the same time, so the voice is ready
# when the longest single sentence is — and the app can start playing
# sentence 1 while the others are still being made (see /voice/speak).
# Very short sentences are joined to the next one (each request has a
# fixed overhead); long ones (Kannada replies are often one long
# sentence) are split at a comma near the middle — a comma is a natural
# pause anyway.
# Previous version: tts_engine_backup_2026-10-09-speed.py
SPEECH_CHUNK_MIN_CHARS = 30
SPEECH_CHUNK_MAX_CHARS = 100

# A "." after these is an abbreviation, not the end of a sentence
# ("Rs. 120000", "B.E. course", "Dr. Rao").
_ABBREVIATION_END = re.compile(r"(?:\b(?:rs|no|dr|mr|mrs|ms|st|vs|etc|approx|sl)|\b[a-z])\.$", re.IGNORECASE)

_client = None


def _get_client() -> SarvamAI:
    global _client
    if _client is None:
        api_key = os.getenv("SARVAM_API_KEY")
        if not api_key:
            raise RuntimeError("SARVAM_API_KEY is not set in .env")
        _client = SarvamAI(api_subscription_key=api_key)
    return _client


def split_text(text: str, max_chars: int) -> list:
    """
    Splits text into chunks of at most max_chars, breaking only at
    sentence ends (. ? ! and the Devanagari danda ।) where possible.
    Shared with transliterator.py and kannada_translator.py, which
    have their own per-request limits.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = re.split(r"(?<=[.?!।])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        # A single sentence longer than the limit gets hard-split.
        while len(sentence) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(sentence[:max_chars])
            sentence = sentence[max_chars:]
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


def _split_long_sentence(sentence: str) -> list:
    """Splits a very long sentence at the comma closest to its middle."""
    if len(sentence) <= SPEECH_CHUNK_MAX_CHARS:
        return [sentence]
    commas = [m.end() for m in re.finditer(r",\s+", sentence)]
    if not commas:
        return [sentence]
    middle = len(sentence) / 2
    cut = min(commas, key=lambda i: abs(i - middle))
    left, right = sentence[:cut].strip(), sentence[cut:].strip()
    if not left or not right:
        return [sentence]
    return _split_long_sentence(left) + _split_long_sentence(right)


def speech_chunks(text: str) -> list:
    """
    The pieces the reply is spoken in: about one sentence each.
    Used by synthesize_speech() and returned to the app as
    "speech_chunks" so it can request and play them one by one.
    """
    text = (text or "").strip()
    if not text:
        return []
    raw = [s.strip() for s in re.split(r"(?<=[.?!।])\s+", text) if s.strip()]

    # Re-join pieces that were cut after an abbreviation ("Rs." / "B.E.").
    sentences = []
    for piece in raw:
        if sentences and _ABBREVIATION_END.search(sentences[-1]):
            sentences[-1] = f"{sentences[-1]} {piece}"
        else:
            sentences.append(piece)

    pieces = [p for s in sentences for p in _split_long_sentence(s)]

    # Join very short pieces to the next one.
    chunks, current = [], ""
    for piece in pieces:
        current = f"{current} {piece}".strip() if current else piece
        if len(current) >= SPEECH_CHUNK_MIN_CHARS:
            chunks.append(current)
            current = ""
    if current:
        # A short last sentence ("Anything else?") is spoken on its own —
        # pieces are made in parallel, so an extra one costs no time.
        # Only a tiny fragment is joined to the previous piece.
        if chunks and len(current) < 12:
            chunks[-1] = f"{chunks[-1]} {current}"
        else:
            chunks.append(current)

    # Safety cap on request size.
    return [c for chunk in chunks for c in split_text(chunk, MAX_CHARS_PER_REQUEST)]


def apply_spoken_forms(text: str, language: str) -> str:
    """Replaces abbreviations with their letter-by-letter spoken form."""
    # Romanized Hinglish/Kannada text gets the English letters, so the
    # sentence doesn't end up in two scripts.
    has_native_script = any(
        "ऀ" <= ch <= "ॿ" or "ಀ" <= ch <= "೿" for ch in text
    )
    form_key = language if has_native_script else "en"

    for abbreviation, forms in SPOKEN_FORMS.items():
        spoken = forms.get(form_key, forms["en"])
        # Only matches when not part of a longer English word. Kannada/
        # Hindi letters directly attached are allowed (e.g. "SVITಗೆ",
        # "SVIT-ನಲ್ಲಿ", "SVIT's" all change).
        # A space is added after it only when a Kannada/Hindi letter is
        # attached directly, so the letters don't run into the suffix.
        pattern = rf"(?<![A-Za-z]){re.escape(abbreviation)}(?![A-Za-z])(?=(\w)?)"
        text = re.sub(
            pattern,
            lambda m: spoken + (" " if m.group(1) and not m.group(1).isascii() else ""),
            text,
            flags=re.IGNORECASE,
        )
    return text


# Indian number units, per language.
NUMBER_UNITS = {
    "en": ("crore", "lakh", "thousand"),
    "kn": ("ಕೋಟಿ", "ಲಕ್ಷ", "ಸಾವಿರ"),
    # 2026-10-12: Hindi had "1 lakh 20 thousand" (English word inside a
    # Hindi reply) or bare digits. Now Hindi words in both scripts.
    "hi": ("करोड़", "लाख", "हज़ार"),            # Devanagari reply
    "hi-Latn": ("crore", "lakh", "hazaar"),    # Hindi in English letters
}


def _indian_number_words(n: int, language: str = "en") -> str:
    """
    325000 -> '3 lakh 25 thousand'   (English)
    325000 -> '3 ಲಕ್ಷ 25 ಸಾವಿರ'      (Kannada)
    12500000 -> '1 crore 25 lakh'
    """
    if n < 1000:
        return str(n)
    crore_w, lakh_w, thousand_w = NUMBER_UNITS.get(language, NUMBER_UNITS["en"])
    parts = []
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, rest = divmod(n, 1000)
    if crore:
        parts.append(f"{crore} {crore_w}")
    if lakh:
        parts.append(f"{lakh} {lakh_w}")
    if thousand:
        parts.append(f"{thousand} {thousand_w}")
    if rest:
        parts.append(str(rest))
    return " ".join(parts)


_RUPEE_AMOUNT = re.compile(
    r"(?:₹|\bRs\.?|\bINR)\s*(\d+(?:,\d{2,3})*)(?:\.\d+)?(?:\s*(?:/-|rupees|rupee))?",
    flags=re.IGNORECASE,
)
_AMOUNT_THEN_RUPEES = re.compile(r"\b(\d+(?:,\d{2,3})*)\s*(rupees|rupee)\b", flags=re.IGNORECASE)
_COMMA_NUMBER = re.compile(r"\b\d{1,3}(?:,\d{2,3})+\b")
# Any number of 5+ digits (10000 and up) — in admission replies these are
# money amounts (years are 4 digits, so "2026" is never touched).
_LARGE_NUMBER = re.compile(r"(?<![\d.])\d{5,}(?!\d)(?!\.\d)")


def speak_numbers(text: str, language: str) -> str:
    """
    Rewrites money amounts so the voice reads them naturally:
        English:  "₹325,000"  -> "3 lakh 25 thousand rupees"
        Kannada:  "₹325,000"  -> "3 ಲಕ್ಷ 25 ಸಾವಿರ ರೂಪಾಯಿ"
                  "325000"    -> "3 ಲಕ್ಷ 25 ಸಾವಿರ"  (Bulbul misread long digit
                                   strings in Kannada, e.g. "90 lakhs" for 325000)
        Hindi:    "₹120,000"  -> "120000 रुपये"
    Also removes thousands-commas from other numbers ("1,166" -> "1166"),
    which the voice was reading as two separate numbers.
    Only affects the text sent to TTS.
    """
    has_native_script = any(
        "ऀ" <= ch <= "ॿ" or "ಀ" <= ch <= "೿" for ch in text
    )
    rupee_word = RUPEE_WORDS[language] if (has_native_script and language in RUPEE_WORDS) else "rupees"

    kannada_script = language == "kn" and has_native_script
    hindi = language == "hi"
    hindi_units = "hi" if has_native_script else "hi-Latn"
    if hindi:
        rupee_word = "रुपये" if has_native_script else "rupaye"

    def amount_to_speech(digits: str) -> str:
        value = int(digits.replace(",", ""))
        if hindi:
            return f"{_indian_number_words(value, hindi_units)} {rupee_word}"
        if language == "en" or not has_native_script:
            return f"{_indian_number_words(value)} {rupee_word}"
        if kannada_script:
            return f"{_indian_number_words(value, 'kn')} {rupee_word}"
        return f"{value} {rupee_word}"

    text = _RUPEE_AMOUNT.sub(lambda m: amount_to_speech(m.group(1)), text)
    if language == "en" or not has_native_script:
        text = _AMOUNT_THEN_RUPEES.sub(lambda m: amount_to_speech(m.group(1)), text)
    text = _COMMA_NUMBER.sub(lambda m: m.group(0).replace(",", ""), text)
    if kannada_script:
        # Remaining long numbers without a ₹ sign ("fee 325000 ರೂಪಾಯಿ",
        # "325000.") are spoken in words too.
        text = _LARGE_NUMBER.sub(lambda m: _indian_number_words(int(m.group(0)), "kn"), text)
    elif hindi:
        # Same for Hindi ("1 lakh 20000" -> "1 lakh 20 hazaar").
        text = _LARGE_NUMBER.sub(lambda m: _indian_number_words(int(m.group(0)), hindi_units), text)
    # "₹120,000 ರೂಪಾಯಿ" became "... ರೂಪಾಯಿ ರೂಪಾಯಿ" — say the word once.
    text = re.sub(r"(ರೂಪಾಯಿ|रुपये|rupaye|rupees)(?:\s+\1)+", r"\1", text)
    return text


def ensure_final_punctuation(text: str) -> str:
    """
    Bulbul can cut off the last word or two when the text doesn't end
    with a sentence-ending mark (seen in case 7: speech stopped
    mid-word with no closing silence). Adds a full stop if missing —
    the Devanagari danda (।) for Hindi script, "." otherwise.
    Only affects the text sent to TTS, never the on-screen text.
    """
    text = text.rstrip()
    if not text or text[-1] in ".?!।":
        return text
    if any("ऀ" <= ch <= "ॿ" for ch in text):
        return text + "।"
    return text + "."


# Silence handling when joining sentence pieces. Each Bulbul clip starts
# with ~0.5 s of silence; joined back-to-back that sounded like dramatic
# announcement pauses ("Big Boss"). Leading/trailing silence is trimmed
# and replaced with one short, natural pause between sentences.
SILENCE_THRESHOLD = 300        # 16-bit amplitude below which audio counts as silence
KEEP_LEAD_SECONDS = 0.05       # tiny lead-in kept before speech starts
PAUSE_BETWEEN_SECONDS = 0.20   # pause inserted between sentences


def _trim_silence(frames: bytes, sample_width: int, channels: int, rate: int,
                  trim_end: bool = True) -> bytes:
    """Removes leading (and optionally trailing) silence from 16-bit PCM."""
    if sample_width != 2:
        return frames  # only 16-bit PCM is handled; leave anything else untouched
    samples = array.array("h", frames)
    step = max(1, int(rate * 0.01)) * channels          # 10 ms windows
    loud = [i for i in range(0, len(samples), step)
            if max((abs(x) for x in samples[i:i + step]), default=0) > SILENCE_THRESHOLD]
    if not loud:
        return frames
    start = max(0, loud[0] - int(rate * KEEP_LEAD_SECONDS) * channels)
    end = min(len(samples), loud[-1] + step) if trim_end else len(samples)
    return samples[start:end].tobytes()


def _merge_wavs(wav_bytes_list: list) -> bytes:
    """
    Joins several WAV clips (same format) into one WAV file, trimming
    each clip's silent edges and inserting a short pause between them.
    The last clip's end is not trimmed, so nothing at the very end is lost.
    """
    output = io.BytesIO()
    with wave.open(io.BytesIO(wav_bytes_list[0]), "rb") as first:
        params = first.getparams()
    sw, ch, rate = params.sampwidth, params.nchannels, params.framerate
    pause = b"\x00" * int(rate * PAUSE_BETWEEN_SECONDS) * sw * ch

    with wave.open(output, "wb") as out:
        out.setparams(params)
        for i, clip in enumerate(wav_bytes_list):
            with wave.open(io.BytesIO(clip), "rb") as w:
                frames = w.readframes(w.getnframes())
            is_last = i == len(wav_bytes_list) - 1
            out.writeframes(_trim_silence(frames, sw, ch, rate, trim_end=not is_last))
            if not is_last:
                out.writeframes(pause)
    return output.getvalue()


# 2026-10-09: audio for a sentence that was already spoken is reused
# (repeated fee replies, the same closing line, ...). Same text + voice +
# speed = identical audio, so nothing changes for the listener.
# Previous version: tts_engine_backup_2026-10-09d.py
AUDIO_CACHE_MAX_ENTRIES = 150
_audio_cache = OrderedDict()
_audio_cache_lock = threading.Lock()


def _convert_chunk(text: str, language_code: str, speaker: str, pace: float) -> list:
    key = (text, language_code, speaker, pace, TTS_MODEL)
    with _audio_cache_lock:
        if key in _audio_cache:
            _audio_cache.move_to_end(key)
            return list(_audio_cache[key])
    clips = _convert_chunk_uncached(text, language_code, speaker, pace)
    if clips:
        with _audio_cache_lock:
            _audio_cache[key] = list(clips)
            while len(_audio_cache) > AUDIO_CACHE_MAX_ENTRIES:
                _audio_cache.popitem(last=False)
    return clips


def _convert_chunk_uncached(text: str, language_code: str, speaker: str, pace: float) -> list:
    client = _get_client()
    try:
        response = client.text_to_speech.convert(
            text=text,
            target_language_code=language_code,
            model=TTS_MODEL,
            speaker=speaker,
            pace=pace,
        )
    except TypeError:
        # Older sarvamai versions named this parameter language_code
        # (see the note in tests/test_sarvam_tts.py).
        response = client.text_to_speech.convert(
            text=text,
            language_code=language_code,
            model=TTS_MODEL,
            speaker=speaker,
            pace=pace,
        )
    return [base64.b64decode(a) for a in response.audios]


def synthesize_speech(text: str, language: str) -> dict:
    """
    Converts text to speech in the given language ("en", "hi", "kn").

    Synchronous (blocking network call) — Engine 5 runs it in a worker
    thread via asyncio.to_thread so it never blocks the server.

    Returns:
        {"success": True, "audio_base64": "...", "audio_format": "wav",
         "language_code": "kn-IN", "speaker": "shubh"}
    or  {"success": False, "error": "..."} — never raises.
    """
    if not text or not text.strip():
        return {"success": False, "error": "empty_text"}

    language_code = LANGUAGE_CODES.get(language, "en-IN")
    speaker = SPEAKERS.get(language, SPEAKERS["en"])
    pace = PACE.get(language, PACE["en"])

    try:
        # Split into sentences first, then prepare each one for speaking
        # (numbers, abbreviations, final full stop) — the same way the
        # app's sentence-by-sentence requests to /voice/speak are prepared.
        chunks = [
            ensure_final_punctuation(apply_spoken_forms(speak_numbers(c, language), language))
            for c in speech_chunks(text)
        ]
        # Convert sentence pieces in parallel; map() keeps them in order.
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as pool:
            results = list(pool.map(
                lambda c: _convert_chunk(c, language_code, speaker, pace), chunks
            ))
        clips = [clip for result in results for clip in result]
        if not clips:
            return {"success": False, "error": "no_audio_returned"}

        wav_bytes = _merge_wavs(clips)
        return {
            "success": True,
            "audio_base64": base64.b64encode(wav_bytes).decode("ascii"),
            "audio_format": "wav",
            "language_code": language_code,
            "speaker": speaker,
        }
    except Exception as e:
        print(f"❌ Sarvam TTS error ({language_code}): {type(e).__name__}: {e}")
        return {"success": False, "error": str(e)}


def save_wav(audio_base64: str, path: str) -> None:
    """Helper for tests — writes the base64 audio to a .wav file."""
    with open(path, "wb") as f:
        f.write(base64.b64decode(audio_base64))
