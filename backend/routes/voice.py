"""
Voice routes — full IntelliVoice pipeline.

    Engine 1 (Language)  ->  Engine 2 (Intelligence)  ->  Engine 3 (Knowledge)
                         ->  Engine 5 (Response + voice)

Memory (Engine 4) is not connected yet — Engine 5 already accepts
conversation_context, so adding it later needs no redesign here.

2026-10-04: integrated Engines 3 and 5 (previously stopped after Engine 2).
2026-10-07: /voice/query accepts an optional `language` (en/hi/kn) so
Whisper can transcribe in the user's chosen language (fast + reliable).
2026-10-09 (speed; previous version in voice_backup_2026-10-09-speed.py):
  - Voice questions: while the transcript corrector runs (~1 s), Engines
    2+3 already start on Whisper's own text. If the corrector changes
    nothing, that work is used as-is (saves ~1 s). If it does fix
    something, the early work is thrown away and Engines 2+3 run again on
    the corrected text — answers are always based on the corrected text.
  - Every reply includes "speech_chunks" (the reply split into
    sentences) and "speech_language". POST /voice/speak turns one chunk
    into audio. The app can call /voice/query with include_audio=false,
    show the text at once, request all chunks in parallel and start
    playing chunk 1 as soon as it arrives — instead of waiting for the
    whole reply's audio.
  - timings_ms["total"] is now the real elapsed time (steps can overlap).
  - (c) When the corrector did change words, the intent found for
    Whisper's text is passed to Engine 2 as a hint: if Sentence
    Transformers agrees on the corrected text, the second Groq intent
    call (~1 s) is skipped. Previous version: voice_backup_2026-10-09c.py
"""

import asyncio
import time
import uuid
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from engines.intelligence_engine import classify_intent
from engines.knowledge_engine import fetch_knowledge
from engines.language_engine import (
    build_language_result,
    correct_transcript,
    no_correction,
    process_text_input,
    set_correction_info,
    speech_to_text,
)
from engines.response_engine import generate_response
from engines.tts_engine import speech_chunks, synthesize_speech

router = APIRouter()

VALID_SCRIPTS = {"native", "romanized"}
VALID_SPEECH_LANGUAGES = {"en", "hi", "kn"}


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
        # Engine 3 catches database exceptions and stores the message —
        # pass it through so the real cause (e.g. "Authentication failed")
        # is visible in test output and API responses.
        if knowledge_result.get("error"):
            summary["error"] = knowledge_result["error"]
    return summary


async def _understand(language_result: dict, confirmed_intent: Optional[str] = None) -> dict:
    """Engines 2 and 3: what is being asked, and the verified facts for it."""
    timings = {}

    start = time.perf_counter()
    intelligence_result = await classify_intent(
        text=language_result["raw_text"],
        normalized_text=language_result["normalized_text"],
        language=language_result["language"]["primary"],
        confirmed_intent=confirmed_intent,
    )
    timings["intelligence"] = _ms(start)

    # Intents with no knowledge_collection (greet, fallback) return
    # immediately without touching the database.
    start = time.perf_counter()
    knowledge_result = await fetch_knowledge(intelligence_result)
    timings["knowledge"] = _ms(start)

    return {"intelligence": intelligence_result, "knowledge": knowledge_result, "timings": timings}


async def _respond(language_result: dict, understanding: dict, session_id: str,
                   input_type: str, script: Optional[str], include_audio: bool,
                   timings: dict, started: float, debug_extra: Optional[dict] = None) -> dict:
    """Engine 5 (reply text + voice) and the API response."""
    intelligence_result = understanding["intelligence"]
    knowledge_result = understanding["knowledge"]
    timings.update(understanding["timings"])

    start = time.perf_counter()
    response_result = await generate_response(
        intelligence_result,
        knowledge_result,
        conversation_context=None,  # Memory Engine not connected yet
        script=script,
        include_audio=include_audio,
    )
    timings["response"] = _ms(start)
    timings["total"] = _ms(started)

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
        "script": response_result["script"],
        "audio_base64": response_result["audio_base64"],
        "audio_format": response_result["audio_format"],
        "tts_success": response_result["tts_success"],

        # For play-as-you-go: send each chunk to POST /voice/speak with
        # this language, play the returned audio in order.
        "speech_chunks": speech_chunks(response_result["response_text_native"]),
        "speech_language": response_result.get("speech_language", response_result["language"]),

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
) -> dict:
    """
    Engines 2 -> 3 -> 5 in order on Engine 1's output (typed questions,
    and tests/test_pipeline.py). Voice questions use the faster
    overlapping path in voice_query().
    """
    started = time.perf_counter() - language_ms / 1000
    understanding = await _understand(language_result)
    return await _respond(language_result, understanding, session_id, input_type,
                          script, include_audio, {"language": language_ms}, started)


def _bad_request(message: str) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": message})


def _validate_script(script: Optional[str]) -> Optional[str]:
    """Normalizes the script field. Empty/missing -> None (use the language default)."""
    if script is None or script.strip() == "":
        return None
    return script.strip().lower()


def _ignore_result(task: asyncio.Task) -> None:
    """Marks a discarded task's outcome as seen (avoids 'exception never retrieved' noise)."""
    if not task.cancelled():
        task.exception()


async def _voice_understanding(audio_bytes: bytes, filename: str, language: Optional[str],
                               started: float):
    """
    Whisper, then the corrector and Engines 2+3 AT THE SAME TIME.
    Returns (language_result, understanding, timings, debug_extra),
    or a JSONResponse on error.
    """
    timings = {}
    try:
        stt = await speech_to_text(audio_bytes, filename, language)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Speech recognition failed: {e}"})
    timings["stt"] = stt["stt_ms"]
    raw_text = stt["raw_text"].strip()
    if not raw_text:
        return _bad_request("Could not hear any speech in the audio")

    correction_task = asyncio.create_task(correct_transcript(raw_text, stt["speech_language"]))

    # Start understanding Whisper's own text while the corrector works.
    start = time.perf_counter()
    early_language = await build_language_result(stt, no_correction(raw_text))
    timings["language_detect"] = _ms(start)
    early_task = asyncio.create_task(_understand(early_language))

    correction = await correction_task
    timings["correction"] = correction["correction_ms"]

    hint = None
    if correction["corrected"]:
        # The corrector fixed something: answer from the corrected text.
        # The early run is usually finishing at about the same moment —
        # wait briefly for its intent, to use as a hint (skips a Groq call
        # when the corrected text agrees). Its facts are NOT reused.
        try:
            early = await asyncio.wait_for(asyncio.shield(early_task), timeout=0.4)
            hint = early["intelligence"]["intent"]
        except Exception:
            early_task.cancel()
            early_task.add_done_callback(_ignore_result)
        language_result = await build_language_result(stt, correction)
        understanding = await _understand(language_result, confirmed_intent=hint)
        early_start_used = False
    else:
        set_correction_info(early_language["language"], correction)
        language_result = early_language
        understanding = await early_task
        early_start_used = True

    timings["understood_at"] = _ms(started)   # elapsed time when the question was fully understood (Engines 1-3)
    return language_result, understanding, timings, {
        "early_start_used": early_start_used,
        "intent_hint_used": hint is not None,
    }


@router.post("/query")
async def voice_query(
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    script: Optional[str] = Form(None),        # "native" | "romanized" | empty = default
    include_audio: bool = Form(True),          # false = text-only reply (faster); use /voice/speak for audio
    language: Optional[str] = Form(None),      # "en" | "hi" | "kn" chosen by the user; used for audio
):
    started = time.perf_counter()
    if not audio and not (text and text.strip()):
        return _bad_request("Provide either audio file or text input")

    script = _validate_script(script)
    if script is not None and script not in VALID_SCRIPTS:
        return _bad_request("script must be 'native' or 'romanized' (or left empty)")

    language = (language or "").strip().lower() or None
    if language is not None and language not in VALID_SPEECH_LANGUAGES:
        return _bad_request("language must be 'en', 'hi' or 'kn' (or left empty)")

    session_id = session_id or str(uuid.uuid4())

    if audio:
        audio_bytes = await audio.read()
        result = await _voice_understanding(audio_bytes, audio.filename, language, started)
        if isinstance(result, JSONResponse):
            return result
        language_result, understanding, timings, debug_extra = result
        return await _respond(language_result, understanding, session_id, "audio",
                              script, include_audio, timings, started, debug_extra)

    # Typed text — no corrector, so the plain in-order pipeline.
    start = time.perf_counter()
    language_result = await process_text_input(text)
    language_ms = _ms(start)
    if not language_result["success"]:
        return JSONResponse(
            status_code=500,
            content={"error": language_result.get("error", "Language processing failed")},
        )
    return await run_pipeline(
        language_result, session_id=session_id, input_type="text",
        script=script, include_audio=include_audio, language_ms=language_ms,
    )


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

    session_id = session_id or str(uuid.uuid4())

    start = time.perf_counter()
    language_result = await process_text_input(text)
    language_ms = _ms(start)

    if not language_result["success"]:
        return _bad_request(language_result.get("error", "Empty text"))

    return await run_pipeline(
        language_result,
        session_id=session_id,
        input_type="text",
        script=script,
        include_audio=include_audio,
        language_ms=language_ms,
    )


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
