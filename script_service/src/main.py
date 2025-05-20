# /home/ubuntu/podcast_workflow_mvp/script_service/src/main.py
import os
import json
from typing import List, Dict, Any, Annotated

import httpx
import openai
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Text,
    ForeignKey,
    Enum as SAEnum,
)
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
from celery import Celery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/podcast_db"
)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY is not set. Script generation will fail.")

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Celery Setup
celery_app = Celery(
    "script_tasks", broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


# SQLAlchemy Models
class ScriptModel(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    length_minutes = Column(Integer, nullable=False)
    status = Column(
        String, default="pending"
    )  # e.g., pending, processing, complete, failed
    raw_script_json = Column(Text)  # Stores the full JSON from OpenAI
    lines = relationship("ScriptLineModel", back_populates="script")


class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    speaker_role = Column(String, nullable=False)  # 'host', 'guest', etc.
    text = Column(Text, nullable=False)
    voice_id = Column(String, nullable=True)  # To be populated based on speaker_role
    line_order = Column(Integer, nullable=False)  # To maintain order
    tts_status = Column(
        String, default="pending"
    )  # e.g., pending, processing, complete, failed
    script = relationship("ScriptModel", back_populates="lines")


Base.metadata.create_all(bind=engine)


# Pydantic Models
class SpeakerInfo(BaseModel):
    role: str
    voice_id: str


class ScriptCreateRequest(BaseModel):
    title: str
    speakers: List[SpeakerInfo]
    length_minutes: int = Field(..., gt=0, le=60)  # Example: 1 to 60 minutes


class ScriptLineResponse(BaseModel):
    speaker: str
    text: str


class ScriptCreateResponse(BaseModel):
    script_id: int
    title: str
    status: str
    # lines: List[ScriptLineResponse] # Optionally return lines if needed immediately


app = FastAPI(title="Script Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# OpenAI Client (ensure API key is set)
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.error("OpenAI API key not found. Script generation will not work.")


async def generate_dialogue_with_openai(
    title: str, speakers_info: List[SpeakerInfo], length_minutes: int
) -> List[Dict[str, str]]:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured.")

    speaker_roles = [s.role for s in speakers_info]
    system_prompt = (
        f"You are a scriptwriter for a podcast. Generate a dialogue for a podcast episode titled '{title}'. "
        f"The episode should be approximately {length_minutes} minutes long. "
        f"The speakers are: {', '.join(speaker_roles)}. "
        f"The output must be a JSON array, where each object has a 'speaker' key (matching one of the provided roles) "
        f"and a 'text' key containing their dialogue. Ensure a natural conversation flow. Do not include any other text or explanation outside the JSON array."
        f"Example: [{{'speaker': '{speakers_info[0].role}', 'text': 'Welcome to the show!'}}, {{'speaker': '{speakers_info[1].role if len(speakers_info) > 1 else speakers_info[0].role}', 'text': 'Thanks for having me.'}} ... ]"
    )

    try:
        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:  # Using httpx for async call
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-3.5-turbo",  # Or a more advanced model if available/preferred
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Generate the dialogue."},
                    ],
                    "response_format": {
                        "type": "json_object"
                    },  # Request JSON output if model supports
                },
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            completion = response.json()

            # Extract the content which should be a JSON string
            # The actual path might vary based on OpenAI's response structure for JSON mode
            # Assuming the JSON string is in choices[0].message.content
            json_content_str = (
                completion.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "[]")
            )

            # Parse the JSON string
            dialogue_json = json.loads(json_content_str)

            # The prompt asks for an array directly, but if it's nested, adjust here.
            # E.g. if it returns {"dialogue": [...]}, then dialogue_json = json.loads(json_content_str).get("dialogue", [])
            if isinstance(dialogue_json, dict) and "dialogue" in dialogue_json:
                dialogue_list = dialogue_json["dialogue"]  # if the model wraps it
            elif isinstance(dialogue_json, list):
                dialogue_list = dialogue_json
            else:
                logger.error(f"Unexpected JSON structure from OpenAI: {dialogue_json}")
                raise ValueError(
                    "OpenAI returned an unexpected JSON structure for the dialogue."
                )

            # Validate structure
            if not all(
                isinstance(line, dict) and "speaker" in line and "text" in line
                for line in dialogue_list
            ):
                logger.error(
                    f"Generated dialogue does not match expected format: {dialogue_list}"
                )
                raise ValueError(
                    "Generated dialogue does not match the expected format of [{'speaker': 'role', 'text': 'dialogue'}]."
                )

            return dialogue_list

    except httpx.HTTPStatusError as e:
        logger.error(
            f"OpenAI API request failed: {e.response.status_code} - {e.response.text}"
        )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"OpenAI API Error: {e.response.text}",
        )
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            f"Error processing OpenAI response: {e}. Response content: {json_content_str if 'json_content_str' in locals() else 'N/A'}"
        )
        raise HTTPException(
            status_code=500, detail=f"Error processing OpenAI response: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during OpenAI call: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred with OpenAI: {str(e)}",
        )


@app.post("/scripts", response_model=ScriptCreateResponse, status_code=201)
async def create_script(request: ScriptCreateRequest, db: Session = Depends(get_db)):
    logger.info(f"Received script creation request: {request.title}")
    try:
        generated_lines = await generate_dialogue_with_openai(
            request.title, request.speakers, request.length_minutes
        )
    except HTTPException as e:
        # Re-raise HTTPExceptions from OpenAI call
        raise e
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate script: {str(e)}"
        )

    if not generated_lines:
        raise HTTPException(
            status_code=500, detail="Script generation returned no lines."
        )

    # Create speaker role to voice_id mapping
    speaker_voice_map = {s.role: s.voice_id for s in request.speakers}

    # Persist to DB
    db_script = ScriptModel(
        title=request.title,
        length_minutes=request.length_minutes,
        raw_script_json=json.dumps(generated_lines),
        status="processing",  # Mark as processing as Celery tasks will be dispatched
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    logger.info(f"Script {db_script.id} created in DB.")

    # Create script lines and dispatch Celery tasks
    for i, line_data in enumerate(generated_lines):
        speaker_role = line_data.get("speaker")
        text = line_data.get("text")
        voice_id = speaker_voice_map.get(speaker_role)

        if not speaker_role or not text:
            logger.warning(f"Skipping line with missing speaker or text: {line_data}")
            continue
        if not voice_id:
            logger.warning(
                f"Skipping line for speaker '{speaker_role}' as voice_id is not mapped."
            )
            # Potentially update script status to 'failed' or 'partial_error'
            continue

        db_line = ScriptLineModel(
            script_id=db_script.id,
            speaker_role=speaker_role,
            text=text,
            voice_id=voice_id,
            line_order=i,
        )
        db.add(db_line)
        db.commit()  # Commit each line or batch commit
        db.refresh(db_line)

        # Emit Celery task for TTS generation
        # Task name should match what tts_service worker expects
        try:
            celery_app.send_task(
                "src.main.generate_tts_for_line",  # Updated task name to match tts_service definition
                args=[db_line.id, voice_id, text],
                queue="tts_queue",  # Ensure this queue name matches tts_service worker's queue
            )
            logger.info(
                f"Dispatched TTS task for line {db_line.id} (script {db_script.id})"
            )
        except Exception as e:
            logger.error(f"Failed to dispatch Celery task for line {db_line.id}: {e}")
            db_line.tts_status = "dispatch_failed"
            db.commit()
            # Potentially update overall script status

    return ScriptCreateResponse(
        script_id=db_script.id, title=db_script.title, status=db_script.status
    )


@app.get("/scripts")
async def list_scripts(status: str = None, db: Session = Depends(get_db)):
    """List all scripts, optionally filtered by status"""
    query = db.query(ScriptModel)

    if status:
        query = query.filter(ScriptModel.status == status)

    scripts = query.all()
    return [
        {
            "script_id": script.id,
            "title": script.title,
            "length_minutes": script.length_minutes,
            "status": script.status,
        }
        for script in scripts
    ]


@app.get("/scripts/{script_id}")  # Basic endpoint to check script status
async def get_script_status(script_id: int, db: Session = Depends(get_db)):
    db_script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
    if not db_script:
        raise HTTPException(status_code=404, detail="Script not found")

    lines = (
        db.query(ScriptLineModel)
        .filter(ScriptLineModel.script_id == script_id)
        .order_by(ScriptLineModel.line_order)
        .all()
    )
    return {
        "script_id": db_script.id,
        "title": db_script.title,
        "status": db_script.status,
        "length_minutes": db_script.length_minutes,
        "lines": [
            {
                "line_id": line.id,
                "speaker": line.speaker_role,
                "text": line.text,
                "voice_id": line.voice_id,
                "tts_status": line.tts_status,
            }
            for line in lines
        ],
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# To run this service (example, adjust for your setup):
# uvicorn script_service.src.main:app --host 0.0.0.0 --port 8000 --reload
