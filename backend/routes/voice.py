"""
Voice routes — full IntelliVoice pipeline.

    Engine 1 (Language)  ->  Engine 2 (Intelligence)  ->  Engine 4 (Memory)
      ->  Engine 3 (Knowledge)  ->  Engine 5 (Response + voice)
      ->  Engine 4 saves the turn, Engine 6 (Analytics) logs it

2026-10-04: integrated Engines 3 and 5 (previously stopped after Engine 2).
2026-10-07: /voice/query accepts an optional `language` (en/hi/kn).
2026-10-09 (speed): Engines 2+3 start on Whisper's text while the
  corrector runs; "speech_chunks" + POST /voice/speak for play-as-you-go;
  the corrected-text re-run reuses the first run's intent as a hint.
2026-10-12 (integration; previous version in voice_backup_2026-10-12.py):
  - Memory Engine (Bhuvana) connected: before Engine 3, this turn's
    entities are merged with what the parent said earlier in the same
    session ("CSE fee?" ... "and for ISE?" keeps the quota/exam). A short
    follow-up Engine 2 can't place continues the previous topic. Each
    finished turn is saved with memory_engine.add_turn().
  - Analytics (Bhuvana) connected: every question is logged in the
    background (never slows or breaks a reply) for the admin dashboard.
  - answer(): one shared entry point used by /voice/query, /voice/text
    and the frontend's POST /api/query (routes/api.py).
"""

import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from database.connection import get_database
from engines.analytics_engine import log_query
from engines.intelligence_engine import _build_output, classify_intent
from engines.knowledge_engine import fetch_knowledge
from engines.language_engine import (
    build_language_result,
    correct_transcript,
    no_correction,
    process_text_input,
    set_correction_info,
    speech_to_text,
)
from engines.memory_engine import memory_engine
from engines.response_engine import generate_response
from engines.tts_engine import speech_chunks, synthesize_speech

router = APIRouter()

VALID_SCRIPTS = {"native", "romanized"}
VALID_SPEECH_LANGUAGES = {"en", "hi", "kn"}
NO_TOPIC_INTENTS = {"greet", "fallback"}

_background_tasks = set()   # keeps analytics tasks alive until they finish


class PipelineError(Exception):
    """A problem to report to the caller (status code + message for the user)."""
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _knowledge_summary(knowledge_result: dict) -> dict:
    """What Engine 3 found — without sending raw database records to the client."""
    summary = {"found": bool(knowledge_result.get("found"))}
    if summary["found"]:
        summary["match_type"] = knowledge_result.get("match_type", "single")
        summary["count"] = knowledge_result.get("count", 1)
        if knowledge_result.get("note") == "broadened_search":
            summary["broadened_search"] = True
    else:
        summary["reason"] = knowledge_result.get("reason")
        if knowledge_result.get("error"):
            summary["error"] = knowledge_result["error"]
    return summary


# ── Engine 4: Memory ────────────────────────────────────────────────────

def _apply_memory(session_id: Optional[str], ir: dict, extra_entities: Optional[dict] = None):
    """
    Merges this turn's entities with the session's earlier ones (Bhuvana's
    memory_engine.resolve_entities) and rebuilds Engine 2's output with
    them, so Engine 3's database filter and the reply agree.
    Returns (intelligence_result, memory_info). Never raises.
    """
    if not session_id:
        return ir, None
    try:
        original = {k: v for k, v in (ir.get("entities") or {}).items() if k != "topic"}
        current = dict(original)
        for key, value in (extra_entities or {}).items():   # "Your Query Context" box
            current.setdefault(key, value)

        context = memory_engine.get_context(session_id)
        last_intent = context.get("last_intent")
        intent, zone = ir["intent"], ir["confidence_zone"]

        follow_up = bool(context.get("turn_count")) and (
            bool(ir.get("needs_memory")) or (last_intent is not None and last_intent == intent)
        )
        # "And for ECE?" — Engine 2 can't place it alone: continue the previous topic.
        if (follow_up and ir.get("needs_memory") and intent == "fallback"
                and last_intent and last_intent not in NO_TOPIC_INTENTS):
            intent, zone = last_intent, "uncertain"

        resolved = memory_engine.resolve_entities(session_id, current, needs_memory=follow_up)
        resolved.pop("topic", None)

        if intent != ir["intent"] or resolved != original:
            new_ir = _build_output(
                query=ir["query"], normalized_query=ir.get("normalized_query", ""),
                language=ir["language"], intent_id=intent, confidence=ir["confidence"],
                confidence_zone=zone, emotion=ir["emotion"], entities=resolved,
            )
            new_ir["needs_memory"] = ir.get("needs_memory", False)
        else:
            new_ir = ir

        memory_info = {
            "topic": new_ir.get("category") if new_ir["intent"] not in NO_TOPIC_INTENTS else None,
            "context_used": [str(v) for k, v in resolved.items() if k not in current],
            "follow_up": follow_up,
            "continued_previous_topic": intent != ir["intent"],
        }
        return new_ir, memory_info
    except Exception as e:
        print(f"⚠️  Memory step skipped: {type(e).__name__}: {e}")
        return ir, None


def _remember_turn(session_id: Optional[str], language_result: dict, ir: dict,
                   response_result: dict) -> None:
    if not session_id or not response_result.get("success"):
        return
    try:
        memory_engine.add_turn(
            session_id,
            user_text=language_result["raw_text"],
            intent=ir["intent"],
            entities=ir.get("entities"),
            response_text=response_result["response_text"],
            language=response_result.get("language"),
        )
    except Exception as e:
        print(f"⚠️  Memory save skipped: {type(e).__name__}: {e}")


def _log_in_background(**kwargs) -> None:
    """Engine 6: saves the question for the admin dashboard. Never blocks the reply."""
    try:
        task = asyncio.create_task(log_query(get_database(), **kwargs))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except Exception as e:
        print(f"⚠️  Analytics log skipped: {e}")


# ── Engines 2+3 and 5 ───────────────────────────────────────────────────

async def _understand(language_result: dict, session_id: Optional[str] = None,
                      confirmed_intent: Optional[str] = None,
                      extra_entities: Optional[dict] = None) -> dict:
    """Engines 2, 4 (memory) and 3: what is being asked, and the verified facts for it."""
    timings = {}

    start = time.perf_counter()
    intelligence_result = await classify_intent(
        text=language_result["raw_text"],
        normalized_text=language_result["normalized_text"],
        language=language_result["language"]["primary"],
        confirmed_intent=confirmed_intent,
    )
    timings["intelligence"] = _ms(start)

    intelligence_result, memory_info = _apply_memory(session_id, intelligence_result, extra_entities)

    # Intents with no knowledge_collection (greet, fallback) return
    # immediately without touching the database.
    start = time.perf_counter()
    knowledge_result = await fetch_knowledge(intelligence_result)
    timings["knowledge"] = _ms(start)

    return {"intelligence": intelligence_result, "knowledge": knowledge_result,
            "memory": memory_info, "timings": timings}


async def _respond(language_result: dict, understanding: dict, session_id: str,
                   input_type: str, script: Optional[str], include_audio: bool,
                   timings: dict, started: float, debug_extra: Optional[dict] = None,
                   reply_language: Optional[str] = None) -> dict:
    """Engine 5 (reply text + voice), memory save, analytics, and the API response."""
    intelligence_result = understanding["intelligence"]
    knowledge_result = understanding["knowledge"]
    timings.update(understanding["timings"])

    engine5_input = intelligence_result
    if reply_language in VALID_SPEECH_LANGUAGES:      # user chose the reply language
        engine5_input = {**intelligence_result, "language": reply_language}

    start = time.perf_counter()
    response_result = await generate_response(
        engine5_input,
        knowledge_result,
        conversation_context=memory_engine.get_context(session_id) if session_id else None,
        script=script,
        include_audio=include_audio,
    )
    timings["response"] = _ms(start)
    timings["total"] = _ms(started)

    _remember_turn(session_id, language_result, intelligence_result, response_result)
    _log_in_background(
        session_id=session_id, text=language_result["raw_text"],
        language=language_result["language"], intelligence_result=intelligence_result,
        knowledge_result=knowledge_result, input_type=input_type,
        response_time_ms=timings["total"],
    )

    debug = dict(response_result["debug"])
    if debug_extra:
        debug.update(debug_extra)

    return {
        "session_id": session_id,
        "input_type": input_type,
        "transcribed_text": language_result["raw_text"],
        "language": language_result["language"],

        # What the frontend shows and plays
        "response_text": response_result["response_text"],
        "response_text_native": response_result["response_text_native"],
        "response_language": response_result["language"],
        "script": response_result["script"],
        "audio_base64": response_result["audio_base64"],
        "audio_format": response_result["audio_format"],
        "tts_success": response_result["tts_success"],

        # For play-as-you-go: send each chunk to POST /voice/speak with
        # this language, play the returned audio in order.
        "speech_chunks": speech_chunks(response_result["response_text_native"]),
        "speech_language": response_result.get("speech_language", response_result["language"]),

        "memory": understanding.get("memory"),

        # How the system understood the query (useful for demo/debug)
        "analysis": {
            "intent": intelligence_result["intent"],
            "category": intelligence_result["category"],
            "confidence": intelligence_result["confidence"],
            "confidence_zone": intelligence_result["confidence_zone"],
            "emotion": intelligence_result["emotion"],
            "entities": intelligence_result["entities"],
            "response_mode": intelligence_result["response_mode"],
            "needs_escalation": intelligence_result["needs_escalation"],
            "needs_memory": intelligence_result["needs_memory"],
        },
        "knowledge": _knowledge_summary(knowledge_result),
        "timings_ms": timings,
        "status": "complete" if response_result["success"] else "response_generation_failed",
        "debug": debug,
    }


async def run_pipeline(
    language_result: dict,
    session_id: str,
    input_type: str,
    script: Optional[str] = None,
    include_audio: bool = True,
    language_ms: int = 0,
    reply_language: Optional[str] = None,
    extra_entities: Optional[dict] = None,
) -> dict:
    """Engines 2 -> 4 -> 3 -> 5 in order (typed questions, tests/test_pipeline.py)."""
    started = time.perf_counter() - language_ms / 1000
    understanding = await _understand(language_result, session_id, extra_entities=extra_entities)
    return await _respond(language_result, understanding, session_id, input_type,
                          script, include_audio, {"language": language_ms}, started,
                          reply_language=reply_language)


def _ignore_result(task: asyncio.Task) -> None:
    """Marks a discarded task's outcome as seen (avoids 'exception never retrieved' noise)."""
    if not task.cancelled():
        task.exception()


async def _voice_understanding(audio_bytes: bytes, filename: str, language: Optional[str],
                               started: float, session_id: Optional[str] = None,
                               extra_entities: Optional[dict] = None):
    """
    Whisper, then the corrector and Engines 2+3 AT THE SAME TIME.
    Returns (language_result, understanding, timings, debug_extra).
    Raises PipelineError.
    """
    timings = {}
    try:
        stt = await speech_to_text(audio_bytes, filename, language)
    except Exception as e:
        raise PipelineError(500, f"Speech recognition failed: {e}")
    timings["stt"] = stt["stt_ms"]
    raw_text = stt["raw_text"].strip()
    if not raw_text:
        raise PipelineError(400, "I couldn't hear anything in that recording. Please try again.")

    correction_task = asyncio.create_task(correct_transcript(raw_text, stt["speech_language"]))

    # Start understanding Whisper's own text while the corrector works.
    start = time.perf_counter()
    early_language = await build_language_result(stt, no_correction(raw_text))
    timings["language_detect"] = _ms(start)
    early_task = asyncio.create_task(_understand(early_language, session_id,
                                                 extra_entities=extra_entities))

    correction = await correction_task
    timings["correction"] = correction["correction_ms"]

    hint = None
    if correction["corrected"]:
        # The corrector fixed something: answer from the corrected text.
        # The early run's intent (if ready) is used only as a hint.
        try:
            early = await asyncio.wait_for(asyncio.shield(early_task), timeout=0.4)
            hint = early["intelligence"]["intent"]
        except Exception:
            early_task.cancel()
            early_task.add_done_callback(_ignore_result)
        language_result = await build_language_result(stt, correction)
        understanding = await _understand(language_result, session_id, confirmed_intent=hint,
                                          extra_entities=extra_entities)
        early_start_used = False
    else:
        set_correction_info(early_language["language"], correction)
        language_result = early_language
        understanding = await early_task
        early_start_used = True

    timings["understood_at"] = _ms(started)
    return language_result, understanding, timings, {
        "early_start_used": early_start_used,
        "intent_hint_used": hint is not None,
    }


async def answer(*, session_id: str, audio_bytes: Optional[bytes] = None,
                 filename: Optional[str] = None, text: Optional[str] = None,
                 language: Optional[str] = None, script: Optional[str] = None,
                 include_audio: bool = True, reply_language: Optional[str] = None,
                 extra_entities: Optional[dict] = None) -> dict:
    """
    The whole pipeline for one question (voice or typed).
    Used by /voice/query, /voice/text and POST /api/query.
    Raises PipelineError with a message meant for the user.
    """
    started = time.perf_counter()
    if audio_bytes:
        language_result, understanding, timings, debug_extra = await _voice_understanding(
            audio_bytes, filename or "audio.wav", language, started, session_id, extra_entities)
        return await _respond(language_result, understanding, session_id, "audio",
                              script, include_audio, timings, started, debug_extra,
                              reply_language=reply_language)

    if not (text and text.strip()):
        raise PipelineError(422, "Please ask a question by voice or by typing.")
    start = time.perf_counter()
    language_result = await process_text_input(text)
    language_ms = _ms(start)
    if not language_result["success"]:
        raise PipelineError(400, language_result.get("error", "Empty question"))
    return await run_pipeline(language_result, session_id=session_id, input_type="text",
                              script=script, include_audio=include_audio,
                              language_ms=language_ms, reply_language=reply_language,
                              extra_entities=extra_entities)


# ── Routes ──────────────────────────────────────────────────────────────

def _bad_request(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": message})


def _validate_script(script: Optional[str]) -> Optional[str]:
    """Normalizes the script field. Empty/missing -> None (use the language default)."""
    if script is None or script.strip() == "":
        return None
    return script.strip().lower()


@router.post("/query")
async def voice_query(
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    script: Optional[str] = Form(None),        # "native" | "romanized" | empty = default
    include_audio: bool = Form(True),          # false = text-only reply (faster); use /voice/speak for audio
    language: Optional[str] = Form(None),      # "en" | "hi" | "kn" chosen by the user; used for audio
):
    if not audio and not (text and text.strip()):
        return _bad_request("Provide either audio file or text input")

    script = _validate_script(script)
    if script is not None and script not in VALID_SCRIPTS:
        return _bad_request("script must be 'native' or 'romanized' (or left empty)")

    language = (language or "").strip().lower() or None
    if language is not None and language not in VALID_SPEECH_LANGUAGES:
        return _bad_request("language must be 'en', 'hi' or 'kn' (or left empty)")

    try:
        return await answer(
            session_id=session_id or str(uuid.uuid4()),
            audio_bytes=await audio.read() if audio else None,
            filename=audio.filename if audio else None,
            text=text, language=language, script=script, include_audio=include_audio,
        )
    except PipelineError as e:
        return JSONResponse(status_code=e.status, content={"error": e.message})


@router.post("/text")
async def text_query(
    text: str = Form(...),
    session_id: Optional[str] = Form(None),
    script: Optional[str] = Form(None),
    include_audio: bool = Form(True),
):
    script = _validate_script(script)
    if script is not None and script not in VALID_SCRIPTS:
        return _bad_request("script must be 'native' or 'romanized' (or left empty)")
    try:
        return await answer(session_id=session_id or str(uuid.uuid4()), text=text,
                            script=script, include_audio=include_audio)
    except PipelineError as e:
        return JSONResponse(status_code=e.status, content={"error": e.message})


@router.post("/speak")
async def speak(
    text: str = Form(...),       # one item from "speech_chunks"
    language: str = Form(...),   # the reply's "speech_language"
):
    """Audio for one piece of a reply (play-as-you-go). Returns WAV as base64."""
    language = language.strip().lower()
    if language not in VALID_SPEECH_LANGUAGES:
        return _bad_request("language must be 'en', 'hi' or 'kn'")
    if not text.strip():
        return _bad_request("text is empty")
    start = time.perf_counter()
    tts = await asyncio.to_thread(synthesize_speech, text, language)
    if not tts["success"]:
        return JSONResponse(status_code=502, content={"error": tts.get("error", "TTS failed")})
    return {
        "audio_base64": tts["audio_base64"],
        "audio_format": tts["audio_format"],
        "tts_ms": _ms(start),
    }
