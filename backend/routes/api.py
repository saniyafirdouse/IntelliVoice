"""
routes/api.py — the endpoint the React frontend (Pooja) calls.

    POST /api/query     (multipart/form-data)   -> see frontend/API_CONTRACT.md §1
    POST /api/transcribe (multipart/form-data)  -> speech to text only (2026-10-31: the
                         mic shows what it heard so the user can fix it before sending)

Runs exactly the same pipeline as /voice/query (routes/voice.py answer():
Whisper + corrector, Engines 2-6, reply cache, voice) and returns the
JSON shape the frontend was built against. Errors use FastAPI's standard
{"detail": "..."} shape, which the chat page shows to the user as-is.

Login is optional: the Authorization header is accepted but not required.
Added 2026-10-12 (integration).
"""

import asyncio
import time
import json
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Request, UploadFile

from engines.intelligence_engine import extract_entities
from engines import user_history
from engines.college_profile import CONTACT
from engines.tts_engine import SPEAKERS, synthesize_speech
from routes.student import optional_user_email
from routes.voice import NoSpeechError, PipelineError, answer
from utils.system_health import count_phone_question, phone_cap_reached, phone_paused, record_problem

router = APIRouter()

MAX_TEXT_CHARS = 500
SOURCE_NAME = "SVIT Admissions Database"

# 2026-10-13: the chat's "Need help from the admissions office?" card.
# Shown when IntelliVoice has no data, the parent needs escalation, or the
# user asks for the office. callback_available tells the page it can offer
# "Request a callback" (POST /api/callback).
HELP_CARD_INTENTS = {"ask_contact_admission_office"}
# Replies after which the page can offer "Download my document checklist" (POST /api/checklist).
CHECKLIST_INTENTS = {"ask_required_documents", "ask_admission_process", "ask_lateral_pg_admission"}
HELP_CONTACT = {"phone": CONTACT["mobile"][0], "email": CONTACT["email"][0]}
HELP_MESSAGES = {
    "not_found": "I don't have this information yet. The admission office can help — call or email them, or ask for a callback.",
    "escalation": "The SVIT admission office can help you personally — call or email them, or ask for a callback.",
    "contact": "You can call or email the admission office, or leave your number and they will call you back.",
}

# "Reply to me in" choice -> (reply language, script)
RESPONSE_LANGUAGES = {
    "same": (None, None),            # same language as the question, default script
    "en": ("en", "native"),
    "kn": ("kn", "native"),          # Kannada script
    "kn-Latn": ("kn", "romanized"),  # Kannada in English letters
    "hi": ("hi", "native"),          # Devanagari
    "hi-Latn": ("hi", "romanized"),  # Hindi in English letters
}
SPEECH_LANGUAGES = {"en", "hi", "kn"}


def _context_entities(context: Optional[str]) -> dict:
    """
    The optional "Your Query Context" box: {"rank", "category", "branch"}.
    Branch/category are typed freely ("cse", "Computer Science", "GM"), so
    they go through Engine 2's own entity matcher to get the database's
    names (CSE, General, ...). Unknown values are simply ignored.
    """
    if not context:
        return {}
    try:
        data = json.loads(context)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    result = {}
    # 2026-10-13: the rank box is used too (rank predictor). "25,000" -> 25000.
    rank_digits = "".join(ch for ch in str(data.get("rank") or "") if ch.isdigit())
    if rank_digits and 1 <= int(rank_digits) <= 500000:
        result["rank"] = int(rank_digits)
    typed = " ".join(str(data.get(k) or "") for k in ("branch", "category")).strip()
    if typed:
        found = extract_entities(typed)
        result.update({k: v for k, v in found.items() if k in ("branch", "category")})
    return result


def _reply_language_label(result: dict) -> str:
    """en | kn | kn-Latn | hi | hi-Latn — the language/script the reply is in."""
    spoken = result.get("speech_language")
    if spoken == "en":
        return "en"
    lang = result.get("response_language") or spoken or "en"
    if lang in ("kn", "hi") and result.get("script") == "romanized":
        return f"{lang}-Latn"
    return lang


def _to_contract(result: dict) -> dict:
    language = result.get("language") or {}
    analysis = result.get("analysis") or {}
    memory = result.get("memory") or {}
    entities = {k: v for k, v in (analysis.get("entities") or {}).items() if k != "topic"}
    needs_escalation = bool(analysis.get("needs_escalation")) or analysis.get("response_mode") == "escalation"
    not_found = (result.get("debug") or {}).get("path") == "not_found"
    # 2026-10-30: personal cases ("can my son get this concession?") -> the office decides: show its contact card
    asked_for_office = analysis.get("intent") in HELP_CARD_INTENTS or bool(analysis.get("personal_case"))
    help_reason = ("escalation" if needs_escalation else "not_found" if not_found
                   else "contact" if asked_for_office else None)

    audio = None
    if result.get("tts_success") and result.get("audio_base64"):
        audio = {
            "format": result.get("audio_format") or "wav",
            "base64": result["audio_base64"],
            "voice": SPEAKERS.get(result.get("speech_language"), "").capitalize() or None,
        }

    return {
        "session_id": result.get("session_id"),
        "transcript": result.get("transcribed_text"),
        "language": {
            "primary": language.get("primary"),
            "confidence": language.get("confidence"),
            "is_code_switched": bool(language.get("is_code_switched")),
        },
        "understanding": {
            "intent": analysis.get("intent"),
            "confidence": analysis.get("confidence"),
            "entities": entities,
            "emotion": analysis.get("emotion"),
            "response_mode": analysis.get("response_mode"),
        },
        "memory": {
            "topic": memory.get("topic"),
            "context_used": memory.get("context_used") or [],
        },
        "response": {
            "text": result.get("response_text"),
            "language": _reply_language_label(result),
        },
        "data": None,
        "audio": audio,
        "escalation": {
            "needed": help_reason is not None,
            "reason": help_reason,
            "message": HELP_MESSAGES.get(help_reason),
            "contact": HELP_CONTACT if help_reason else None,
            "callback_available": help_reason is not None,
        },
        "source": SOURCE_NAME if (result.get("knowledge") or {}).get("found") else None,
        "checklist_available": analysis.get("intent") in CHECKLIST_INTENTS,
        # 2026-10-15: College-at-a-glance card (only for "tell me everything" questions)
        "overview": result.get("overview"),
        # 2026-10-29: PDF buttons under the reply (bus routes, brochure)
        "documents": result.get("documents") or [],
        # extra (ignored by the page, useful when testing)
        "timings_ms": result.get("timings_ms"),
    }


# ── Per-visitor limit (2026-11-01, for the expo) ──────────────────────────
# A visitor on their own phone (through the Cloudflare tunnel) can ask at most
# VISITOR_LIMIT spoken-reply questions per VISITOR_WINDOW_S, so one person (or a
# prank) can't use up the Groq / Sarvam credits. Not limited:
#   - the laptop itself (requests that did not come through the tunnel),
#   - text-only answers (Help & FAQ), which use no Sarvam voice.
# A visitor = the browser's own random id (X-Visitor-Id), else their internet address.
VISITOR_LIMIT = 10
VISITOR_WINDOW_S = 5 * 60
_visitor_hits: dict = {}


def _check_phone_access(request: Request) -> bool:
    """True if this request came through the tunnel (a visitor's phone). Raises if phones are paused."""
    if not request.headers.get("cf-connecting-ip"):
        return False                        # the stall laptop: never paused or limited
    if phone_paused():
        raise HTTPException(503, detail="Phone access is paused right now. Please use the IntelliVoice laptop at the stall.")
    return True


def _check_visitor_limit(request: Request) -> None:
    tunnel_ip = request.headers.get("cf-connecting-ip")
    if not tunnel_ip:                       # not through the tunnel = the stall laptop: never limited
        return
    if phone_cap_reached():                 # 2026-11-01: all phones together, per hour
        raise HTTPException(429, detail="Eva is very busy right now. Please try again in a few minutes, or use the IntelliVoice laptop at the stall.")
    visitor = (request.headers.get("x-visitor-id") or "").strip()[:64] or tunnel_ip
    now = time.time()
    hits = [t for t in _visitor_hits.get(visitor, []) if now - t < VISITOR_WINDOW_S]
    if len(hits) >= VISITOR_LIMIT:
        wait_min = max(1, round((VISITOR_WINDOW_S - (now - hits[0])) / 60))
        _visitor_hits[visitor] = hits
        raise HTTPException(429, detail=(f"You've asked {VISITOR_LIMIT} questions in {VISITOR_WINDOW_S // 60} minutes. "
                                         f"Please wait about {wait_min} minute{'s' if wait_min != 1 else ''} and ask again."))
    hits.append(now)
    _visitor_hits[visitor] = hits
    count_phone_question()
    if len(_visitor_hits) > 5000:           # keep memory small: forget visitors idle for a while
        for key in [k for k, v in _visitor_hits.items() if not v or now - v[-1] > VISITOR_WINDOW_S]:
            _visitor_hits.pop(key, None)


@router.post("/query")
async def api_query(
    request: Request,
    session_id: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    context: Optional[str] = Form(None),
    speech_language: str = Form("auto"),
    response_language: str = Form("same"),
    include_audio: bool = Form(True),     # 2026-11-01: false = text only (Help & FAQ answers, no Sarvam voice)
    authorization: Optional[str] = Header(None),
):
    _check_phone_access(request)               # 2026-11-01: admin can pause phone visitors
    if include_audio:
        _check_visitor_limit(request)          # 2026-11-01: expo per-visitor limit + hourly cap for all phones
    if not audio and not (text and text.strip()):
        raise HTTPException(422, detail="Please ask a question by voice or by typing.")
    if text and len(text) > MAX_TEXT_CHARS:
        raise HTTPException(400, detail=f"Please keep typed questions under {MAX_TEXT_CHARS} characters.")

    speech = (speech_language or "").strip().lower()
    speech = speech if speech in SPEECH_LANGUAGES else None          # "auto" -> detect
    reply_language, script = RESPONSE_LANGUAGES.get((response_language or "same").strip(), (None, None))

    audio_bytes = await audio.read() if audio else None
    if audio is not None and not audio_bytes and not (text and text.strip()):
        raise HTTPException(400, detail="I couldn't hear anything in that recording. Please try again.")

    try:
        result = await answer(
            session_id=session_id,
            audio_bytes=audio_bytes or None,
            filename=audio.filename if audio else None,
            text=text,
            language=speech,
            script=script,
            include_audio=include_audio,
            reply_language=reply_language,
            extra_entities=_context_entities(context),
        )
    except NoSpeechError:
        # 2026-10-28: silence / noise only — the app shows a small hint, no reply
        return {"status": "no_speech", "session_id": session_id,
                "message": "I didn't hear anything. Tap the mic and try again."}
    except PipelineError as e:
        record_problem("Pipeline", f"{e.status}: {e.message}")     # 2026-11-01: admin "System health"
        raise HTTPException(e.status, detail=e.message)

    # Memory across visits: remember this question for a logged-in student (background, never blocks).
    email = optional_user_email(authorization)
    if email:
        analysis = result.get("analysis") or {}
        asyncio.create_task(user_history.record_turn(
            email, result.get("transcribed_text") or text or "", analysis.get("intent"),
            analysis.get("entities"), (result.get("language") or {}).get("primary")))
    return _to_contract(result)


# ── Speech to text only (2026-10-31) ─────────────────────────────────────
# The mic button now shows the words it heard in the question box first; the
# user can correct them and then press Send (sent as a normal question). Uses
# the same speech recognition + college-word fixes as a spoken question.
@router.post("/transcribe")
async def api_transcribe(
    request: Request,
    audio: UploadFile = File(...),
    speech_language: str = Form("auto"),
):
    _check_phone_access(request)               # 2026-11-01: paused phones can't use the mic either
    from engines.language_engine import correct_transcript, speech_to_text
    audio_bytes = await audio.read()
    if not audio_bytes:
        return {"status": "no_speech", "message": "I didn't hear anything. Tap the mic and try again."}
    speech = (speech_language or "").strip().lower()
    speech = speech if speech in SPEECH_LANGUAGES else None
    try:
        stt = await speech_to_text(audio_bytes, audio.filename or "audio.webm", speech)
    except Exception as e:
        raise HTTPException(500, detail=f"Speech recognition failed. Please try again or type your question. ({type(e).__name__})")
    raw = (stt.get("raw_text") or "").strip()
    if not raw or stt.get("clarity") == "silent":
        return {"status": "no_speech", "message": "I didn't hear anything. Tap the mic and try again."}
    fixed = await correct_transcript(raw, stt.get("speech_language"))
    return {
        "status": "ok",
        "text": fixed.get("text") or raw,
        "language": stt.get("speech_language"),
        "unclear": stt.get("clarity") == "unclear",
    }


# 2026-11-01: "Hey Eva" -> Eva says hello before listening. The spoken greeting is made
# once per language and kept in memory, so it costs one Sarvam voice request per
# language per backend start (not one per visitor).
GREETINGS = {
    "en": "Hello there, I'm listening. What would you like to know?",
    "hi": "नमस्ते, मैं सुन रही हूँ। बताइए, आप क्या जानना चाहेंगे?",
    "kn": "ನಮಸ್ಕಾರ, ನಾನು ಕೇಳ್ತಾ ಇದ್ದೀನಿ. ಏನು ತಿಳ್ಕೋಬೇಕು ಹೇಳಿ?",
}
_greeting_cache: dict = {}


@router.get("/greeting")
async def api_greeting(language: str = "en"):
    lang = language if language in GREETINGS else "en"
    if lang not in _greeting_cache:
        tts = await asyncio.to_thread(synthesize_speech, GREETINGS[lang], lang)
        audio = ({"format": tts.get("audio_format") or "wav", "base64": tts["audio_base64"],
                  "voice": SPEAKERS.get(lang)} if tts.get("success") else None)
        if audio is None:      # no voice now (e.g. no credits): show the text, try the voice again next time
            return {"response": {"text": GREETINGS[lang], "language": lang}, "audio": None}
        _greeting_cache[lang] = {"response": {"text": GREETINGS[lang], "language": lang}, "audio": audio}
    return _greeting_cache[lang]
