# /home/ubuntu/podcast_workflow_mvp/script_service/src/main.py
import os
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
import httpx

# Import from our modules
from .models import (
    Base,
    ScriptModel,
    ScriptLineModel,
    ScriptCreateRequest,
    ScriptCreateResponse,
    ScriptDetailsResponse,
)
from .database import engine, get_db
from .script_generator import generate_script

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TTS_SERVICE_URL = os.getenv("TTS_SERVICE_URL", "http://tts_service:8000")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set. Script generation will fail.")

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(title="Script Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.post("/scripts", response_model=ScriptCreateResponse, status_code=201)
async def create_script(request: ScriptCreateRequest, db: Session = Depends(get_db)):
    """
    Create a new podcast script based on the specified format and questionnaire answers.

    - interview: Two-person conversation (host + single guest)
    - roundtable: Multiple-person discussion (host + multiple guests)
    - article: Discussion of an article or blog post
    """
    logger.info(f"Received script creation request: {request.title}")

    try:
        # Convert SpeakerInfo Pydantic models to dictionaries for the script generator
        speakers_dict = [speaker.dict() for speaker in request.speakers]
        questionnaire_dict = [qa.dict() for qa in request.questionnaire_answers]

        # Generate the script using our LangChain-based generator
        generated_lines = await generate_script(
            format_type=request.format_type,
            title=request.title,
            speakers=speakers_dict,
            questionnaire_answers=questionnaire_dict,
            length_minutes=request.length_minutes,
            article_url=request.article_url,
        )
    except ValueError as e:
        logger.error(f"Script generation failed with ValueError: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate script: {str(e)}"
        )

    if not generated_lines:
        raise HTTPException(
            status_code=500, detail="Script generation returned no lines."
        )

    # Create speaker role to voice_id and name mapping
    # Handle both frontend roles (guest) and OpenAI generated roles (guest1, guest2, etc.)
    speaker_map = {}

    # Add exact role matches
    for speaker in request.speakers:
        speaker_map[speaker.role] = {"voice_id": speaker.voice_id, "name": speaker.name}

    # Add numbered guest mappings for OpenAI compatibility
    guest_speakers = [s for s in request.speakers if s.role == "guest"]
    for i, guest in enumerate(guest_speakers, 1):
        speaker_map[f"guest{i}"] = {"voice_id": guest.voice_id, "name": guest.name}

    logger.info(f"Speaker mapping created: {list(speaker_map.keys())}")

    # Persist to DB
    db_script = ScriptModel(
        title=request.title,
        length_minutes=request.length_minutes,
        format_type=request.format_type,
        raw_script_json=json.dumps(generated_lines),
        questionnaire_json=json.dumps(
            [qa.dict() for qa in request.questionnaire_answers]
        ),
        status="processing",  # Mark as processing as Celery tasks will be dispatched
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    logger.info(f"Script {db_script.id} created in DB.")

    # Create script lines and save to database
    for i, line_data in enumerate(generated_lines):
        speaker_role = line_data.get("speaker_role")
        speaker_name = line_data.get("speaker_name")
        text = line_data.get("text")

        # Get voice_id from our speaker mapping
        speaker_info = speaker_map.get(speaker_role)
        voice_id = speaker_info["voice_id"] if speaker_info else None

        if not speaker_role or not text:
            logger.warning(f"Skipping line with missing speaker or text: {line_data}")
            continue
        if not voice_id:
            logger.warning(f"Skipping line for speaker '{speaker_role}' - no voice_id")
            continue

        db_line = ScriptLineModel(
            script_id=db_script.id,
            speaker_role=speaker_role,
            speaker_name=speaker_name,
            text=text,
            voice_id=voice_id,
            line_order=i,
        )
        db.add(db_line)
        db.commit()  # Commit each line or batch commit
        db.refresh(db_line)

        # NOTE: TTS task generation removed - will be triggered separately through Admin UI

    return ScriptCreateResponse(
        script_id=db_script.id, title=db_script.title, status=db_script.status
    )


@app.post("/scripts/{script_id}/generate-tts")
async def generate_tts_for_script(script_id: int, db: Session = Depends(get_db)):
    """
    Trigger TTS generation for all lines in a script.

    This endpoint makes a request to the TTS service to process the script
    lines sequentially.
    """
    # First check if script exists
    db_script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")

    try:
        # Make a request to the TTS service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{TTS_SERVICE_URL}/tts/process-script/{script_id}"
            )

            if response.status_code != 200:
                error_detail = response.json().get("detail", str(response.content))
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"TTS Service error: {error_detail}",
                )

            result = response.json()

            # Update script status
            db_script.status = "tts_processing"
            db.commit()

            return {
                "script_id": script_id,
                "status": "tts_processing",
                "message": f"TTS generation started. {result.get('processed_lines', 0)} lines processed.",
            }

    except httpx.RequestError as e:
        logger.error(f"Error connecting to TTS service: {e}")
        raise HTTPException(
            status_code=503,
            detail="Could not connect to TTS service. Please try again later.",
        )


@app.get("/scripts", response_model=List[ScriptCreateResponse])
async def list_scripts(status: Optional[str] = None, db: Session = Depends(get_db)):
    """List all scripts, optionally filtered by status"""
    query = db.query(ScriptModel)

    if status:
        query = query.filter(ScriptModel.status == status)

    scripts = query.all()
    return [
        ScriptCreateResponse(
            script_id=script.id, title=script.title, status=script.status
        )
        for script in scripts
    ]


@app.get("/scripts/{script_id}", response_model=ScriptDetailsResponse)
async def get_script_status(script_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific script"""
    db_script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")

    lines = (
        db.query(ScriptLineModel)
        .filter(ScriptLineModel.script_id == script_id)
        .order_by(ScriptLineModel.line_order)
        .all()
    )

    return ScriptDetailsResponse(
        script_id=db_script.id,
        title=db_script.title,
        format_type=db_script.format_type,
        status=db_script.status,
        length_minutes=db_script.length_minutes,
        lines=[
            {
                "line_id": line.id,
                "speaker_role": line.speaker_role,
                "speaker_name": line.speaker_name,
                "text": line.text,
                "voice_id": line.voice_id,
                "tts_status": line.tts_status,
                "avatar_status": line.avatar_status,
                "audio_file_path": line.audio_file_path,
                "video_file_path": line.video_file_path,
                "speaker_image_path": line.speaker_image_path,
            }
            for line in lines
        ],
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.delete("/scripts/{script_id}")
async def delete_script(script_id: int, db: Session = Depends(get_db)):
    """Delete a script and all associated script lines"""
    # Check if script exists
    db_script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")

    try:
        # Delete all associated script lines first
        db.query(ScriptLineModel).filter(
            ScriptLineModel.script_id == script_id
        ).delete()

        # Delete the script
        db.delete(db_script)
        db.commit()

        logger.info(f"Script {script_id} deleted successfully")
        return {"message": f"Script {script_id} deleted successfully"}

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete script {script_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete script: {str(e)}"
        )


@app.put("/scripts/lines/{line_id}")
async def update_script_line(line_id: int, text: str, db: Session = Depends(get_db)):
    """Update the text content of a specific script line"""
    # Find the script line
    db_line = db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()
    if not db_line:
        raise HTTPException(status_code=404, detail="Script line not found")

    try:
        # Update the text
        db_line.text = text
        db.commit()
        db.refresh(db_line)

        logger.info(f"Script line {line_id} updated successfully")
        return {
            "message": f"Script line {line_id} updated successfully",
            "line_id": line_id,
            "text": text,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update script line {line_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update script line: {str(e)}"
        )


# To run this service (example, adjust for your setup):
# uvicorn script_service.src.main:app --host 0.0.0.0 --port 8000 --reload
