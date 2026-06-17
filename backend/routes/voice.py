from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from engines.language_engine import transcribe_audio, process_text_input
from typing import Optional

router = APIRouter()


# ── Voice query endpoint ───────────────────────────────────────────────────
@router.post("/query")
async def voice_query(
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    # Validate: must have either audio or text
    if not audio and not text:
        return JSONResponse(
            status_code=400,
            content={"error": "Provide either audio file or text input"}
        )

    # Process audio input
    if audio:
        audio_bytes = await audio.read()
        language_result = await transcribe_audio(audio_bytes, audio.filename)
    else:
        # Process text input
        language_result = await process_text_input(text)

    if not language_result["success"]:
        return JSONResponse(
            status_code=500,
            content={"error": language_result.get("error", "Processing failed")}
        )

    # For now return language engine output
    # Tomorrow Engine 2 will plug in here
    return {
        "session_id": session_id or "no-session",
        "input_type": "audio" if audio else "text",
        "transcribed_text": language_result["raw_text"],
        "normalized_text": language_result["normalized_text"],
        "language": language_result["language"],
        "status": "language_engine_complete",
        "next": "intelligence_engine_pending"
    }


# ── Text only endpoint (simpler testing) ──────────────────────────────────
@router.post("/text")
async def text_query(
    text: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    result = await process_text_input(text)
    return {
        "session_id": session_id or "no-session",
        "input_type": "text",
        "transcribed_text": result["raw_text"],
        "normalized_text": result["normalized_text"],
        "language": result["language"],
        "status": "language_engine_complete"
    }