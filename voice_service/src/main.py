# /home/ubuntu/podcast_workflow_mvp/voice_service/src/main.py
import os
import shutil
import tempfile
from typing import List, Annotated

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

# ElevenLabs SDK
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import Voice

# Environment Variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/podcast_db"
)
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
MEDIA_DIR = os.getenv("MEDIA_DIR", "/data")
MEDIA_VOICE_IMAGES_DIR = os.getenv("MEDIA_VOICE_IMAGES_DIR", "/data/voice-images")

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Create media directory if it doesn_t exist
if not os.path.exists(MEDIA_VOICE_IMAGES_DIR):
    try:
        os.makedirs(MEDIA_VOICE_IMAGES_DIR)
        print(f"Created media directory: {MEDIA_VOICE_IMAGES_DIR}")
    except OSError as e:
        print(f"Error creating media directory {MEDIA_VOICE_IMAGES_DIR}: {e}")


# SQLAlchemy Model for Voices
class VoiceModel(Base):
    __tablename__ = "voices"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    voice_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    image_path = Column(String, nullable=True)  # Stores path to locally saved image


Base.metadata.create_all(bind=engine)  # Create table if it doesn_t exist


# Pydantic Models
class VoiceCreateResponse(BaseModel):
    voice_id: str


class VoiceListResponse(BaseModel):
    id: int
    voice_id: str
    name: str
    image_path: str | None = None  # Stores path to locally saved image


app = FastAPI(title="Voice Service")

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


@app.post("/voices", response_model=VoiceCreateResponse)
async def clone_voice(
    name: Annotated[str, Form()],
    speaker_image: Annotated[UploadFile | None, File()] = None,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if not ELEVEN_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVEN_API_KEY not configured")
    if not files:
        raise HTTPException(
            status_code=400, detail="No files provided for voice cloning"
        )

    # Basic validation for audio files
    for f in files:
        if f.content_type not in [
            "audio/mpeg",
            "audio/wav",
            "audio/x-wav",
            "audio/mp3",
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio file type: {f.content_type}. Please use MP3 or WAV.",
            )

    saved_image_path = None
    if speaker_image:
        if speaker_image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image file type: {speaker_image.content_type}. Please use JPEG, PNG, or WebP.",
            )

        import time
        import re

        timestamp = int(time.time())
        sanitized_filename = re.sub(
            r"[^a-zA-Z0-9_.-]", "_", speaker_image.filename or f"image_{timestamp}"
        )
        image_filename = f"{timestamp}_{sanitized_filename}"
        saved_image_path = os.path.join(MEDIA_VOICE_IMAGES_DIR, image_filename)

        try:
            with open(saved_image_path, "wb") as buffer:
                shutil.copyfileobj(speaker_image.file, buffer)
            print(f"Speaker image saved to: {saved_image_path}")
        except Exception as e:
            print(f"Error saving speaker image: {e}")
            raise HTTPException(
                status_code=500, detail=f"Could not save speaker image: {e}"
            )

    temp_audio_files_paths = []
    try:
        # Save uploaded audio files to temporary local paths for the SDK
        for uploaded_file in files:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=os.path.splitext(uploaded_file.filename)[1]
            ) as tmp_file:
                shutil.copyfileobj(uploaded_file.file, tmp_file)
                temp_audio_files_paths.append(tmp_file.name)

        client = AsyncElevenLabs(api_key=ELEVEN_API_KEY)

        # Use ElevenLabs SDK to add voice
        cloned_voice: Voice = await client.voices.add(
            name=name,
            description=f"Voice for {name}",  # Optional description
            files=temp_audio_files_paths,
        )

        cloned_voice_id = cloned_voice.voice_id

        if not cloned_voice_id:
            raise HTTPException(
                status_code=500,
                detail="Failed to get voice_id from ElevenLabs SDK response",
            )

        # Store in DB
        db_voice = VoiceModel(
            voice_id=cloned_voice_id, name=name, image_path=saved_image_path
        )
        db.add(db_voice)
        db.commit()
        db.refresh(db_voice)
        return VoiceCreateResponse(voice_id=cloned_voice_id)

    except Exception as e:
        # Log the exception e
        print(
            f"Error during voice cloning with SDK: {e}"
        )  # Replace with proper logging
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during voice cloning: {str(e)}",
        )
    finally:
        # Clean up temporary audio files
        for path in temp_audio_files_paths:
            if os.path.exists(path):
                os.remove(path)


@app.get("/voices", response_model=List[VoiceListResponse])
async def list_voices(db: Session = Depends(get_db)):
    voices = db.query(VoiceModel).all()
    return voices


@app.get("/health")
async def health_check():
    return {"status": "ok"}
