"""
routes/api.py — the endpoint the React frontend (Pooja) calls.

    POST /api/query     (multipart/form-data)   -> see frontend/API_CONTRACT.md §1

Runs exactly the same pipeline as /voice/query (routes/voice.py answer():
Whisper + corrector, Engines 2-6, reply cache, voice) and returns the
JSON shape the frontend was built against. Errors use FastAPI's standard
{"detail": "..."} shape, which the chat page shows to the user as-is.

Login is optional: the Authorization header is accepted but not required.
Added 2026-10-12 (integration).
"""

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from engines.intelligence_engine import extract_entities
from engines.tts_engine import SPEAKERS
from routes.voice import PipelineError, answer

router = APIRouter()

MAX_TEXT_CHARS = 500
SOURCE_NAME = "SVIT Admissions Database"

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
    typed = " ".join(str(data.get(k) or "") for k in ("branch", "category")).strip()
    if not typed:
        return {}
    found = extract_entities(typed)
    return {k: v for k, v in found.items() if k in ("branch", "category")}


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
        "escalation": {"needed": needs_escalation, "message": None, "contact": None},
        "source": SOURCE_NAME if (result.get("knowledge") or {}).get("found") else None,
        # extra (ignored by the page, useful when testing)
        "timings_ms": result.get("timings_ms"),
    }


@router.post("/query")
async def api_query(
    session_id: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    context: Optional[str] = Form(None),
    speech_language: str = Form("auto"),
    response_language: str = Form("same"),
):
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
            include_audio=True,
            reply_language=reply_language,
            extra_entities=_context_entities(context),
        )
    except PipelineError as e:
        raise HTTPException(e.status, detail=e.message)
    return _to_contract(result)
