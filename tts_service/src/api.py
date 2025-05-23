# /home/ubuntu/podcast_workflow_mvp/tts_service/src/api.py
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .database import get_db
from .models import ScriptLineModel
from .tts_processor import process_line_tts

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="TTS Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://podcast-workflow-mvp.vercel.app",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Pydantic models for API
class TTSProcessResponse(BaseModel):
    script_id: int
    status: str
    message: str
    processed_lines: int


@app.post("/tts/process-script/{script_id}", response_model=TTSProcessResponse)
async def process_script_tts(script_id: int, db: Session = Depends(get_db)):
    """
    Process TTS for all lines in a script sequentially.

    This endpoint will process each line one by one without using Celery tasks,
    ensuring that the requests to ElevenLabs are not made concurrently.
    """
    # Check if script exists
    script_lines = (
        db.query(ScriptLineModel)
        .filter(ScriptLineModel.script_id == script_id)
        .order_by(ScriptLineModel.line_order)
        .all()
    )

    if not script_lines:
        raise HTTPException(
            status_code=404, detail=f"No lines found for script {script_id}"
        )

    # Process each line sequentially
    processed_count = 0
    for line in script_lines:
        # Skip lines that are already complete or in processing
        if line.tts_status in ["complete", "processing"]:
            continue

        # Process the line
        success = process_line_tts(
            db=db, line_id=line.id, voice_id=line.voice_id, text=line.text
        )

        if success:
            processed_count += 1

    return TTSProcessResponse(
        script_id=script_id,
        status="complete",
        message=f"Processed {processed_count} lines for script {script_id}",
        processed_lines=processed_count,
    )


@app.post("/tts/process-line/{line_id}")
async def process_single_line_tts(line_id: int, db: Session = Depends(get_db)):
    """Process TTS for a single script line"""
    # Get the line
    line = db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()

    if not line:
        raise HTTPException(status_code=404, detail=f"Line {line_id} not found")

    # Process the line
    success = process_line_tts(
        db=db, line_id=line.id, voice_id=line.voice_id, text=line.text
    )

    if success:
        return {
            "message": f"Line {line_id} processed successfully",
            "status": "complete",
        }
    else:
        raise HTTPException(status_code=500, detail=f"Failed to process line {line_id}")


@app.get("/tts/line-status/{line_id}")
async def get_line_tts_status(line_id: int, db: Session = Depends(get_db)):
    """Get TTS status for a specific line"""
    line = db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()

    if not line:
        raise HTTPException(status_code=404, detail=f"Line {line_id} not found")

    return {
        "line_id": line_id,
        "tts_status": line.tts_status,
        "audio_file_path": line.audio_file_path,
    }


@app.get("/tts/audio/{line_id}")
async def get_line_audio(line_id: int, db: Session = Depends(get_db)):
    """Redirect to audio file URL in Supabase Storage"""
    line = db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()

    if not line:
        raise HTTPException(status_code=404, detail=f"Line {line_id} not found")

    if not line.audio_file_path:
        raise HTTPException(status_code=404, detail="Audio file not found")

    # Redirect to the Supabase Storage URL
    return RedirectResponse(url=line.audio_file_path)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
