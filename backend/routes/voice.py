from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from engines.language_engine import transcribe_audio, process_text_input
from engines.intelligence_engine import classify_intent
from typing import Optional
import uuid

router = APIRouter()


@router.post("/query")
async def voice_query(
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    if not audio and not text:
        return JSONResponse(
            status_code=400,
            content={"error": "Provide either audio file or text input"}
        )

    # Generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())

    # Engine 1: Language Understanding
    if audio:
        audio_bytes = await audio.read()
        language_result = await transcribe_audio(audio_bytes, audio.filename)
    else:
        language_result = await process_text_input(text)

    if not language_result["success"]:
        return JSONResponse(
            status_code=500,
            content={"error": language_result.get("error", "Processing failed")}
        )

    # Engine 2: AI Intelligence
    intelligence_result = await classify_intent(
        text=language_result["raw_text"],
        normalized_text=language_result["normalized_text"],
        language=language_result["language"]["primary"]
    )

    return {
        "session_id": session_id,
        "input_type": "audio" if audio else "text",
        "transcribed_text": language_result["raw_text"],
        "language": language_result["language"],

        "intent": intelligence_result["intent"],
        "category": intelligence_result["category"],
        "confidence": intelligence_result["confidence"],
        "confidence_zone": intelligence_result["confidence_zone"],

        "emotion": intelligence_result["emotion"],
        "entities": intelligence_result["entities"],

        "knowledge_request": intelligence_result["knowledge_request"],
        "response_mode": intelligence_result["response_mode"],
        "needs_memory": intelligence_result["needs_memory"],
        "needs_escalation": intelligence_result["needs_escalation"],

        "status": "intelligence_engine_complete",
        "next": "knowledge_engine_pending"
    }


@router.post("/text")
async def text_query(
    text: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    if not session_id:
        session_id = str(uuid.uuid4())

    language_result = await process_text_input(text)
    intelligence_result = await classify_intent(
        text=language_result["raw_text"],
        normalized_text=language_result["normalized_text"],
        language=language_result["language"]["primary"]
    )

    return {
        "session_id": session_id,
        "input_type": "text",
        "transcribed_text": language_result["raw_text"],
        "language": language_result["language"],

        "intent": intelligence_result["intent"],
        "category": intelligence_result["category"],
        "confidence": intelligence_result["confidence"],
        "confidence_zone": intelligence_result["confidence_zone"],

        "emotion": intelligence_result["emotion"],
        "entities": intelligence_result["entities"],

        "knowledge_request": intelligence_result["knowledge_request"],
        "response_mode": intelligence_result["response_mode"],
        "needs_memory": intelligence_result["needs_memory"],
        "needs_escalation": intelligence_result["needs_escalation"],

        "status": "intelligence_engine_complete"
    }