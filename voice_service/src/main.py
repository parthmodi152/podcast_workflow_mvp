# /home/ubuntu/podcast_workflow_mvp/voice_service/src/main.py
from typing import List, Annotated, Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import from our modules
from .models import (
    Base,
    VoiceModel,
    VoiceCreateResponse,
    VoiceListResponse,
    VoiceImageResponse,
)
from .database import engine, get_db
from .utils import (
    ensure_media_directories,
    save_audio_files_temp,
    cleanup_temp_files,
    save_speaker_image,
    cleanup_speaker_image,
)
from .elevenlabs_client import ElevenLabsClient

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

# Ensure media directories exist
ensure_media_directories()

# Create FastAPI app
app = FastAPI(title="Voice Service")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost:3001",  # Local development alternate port
        "https://podcast-workflow-mvp.vercel.app",  # Vercel deployment
        "https://*.vercel.app",  # All Vercel deployments
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.post("/voices", response_model=VoiceCreateResponse)
async def clone_voice(
    name: Annotated[str, Form()],
    files: List[UploadFile] = File(...),
    speaker_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # Validate the API key is configured
    elevenlabs_client = ElevenLabsClient()
    if not elevenlabs_client.api_key:
        api_key_error = "ELEVEN_API_KEY not configured"
        raise HTTPException(status_code=500, detail=api_key_error)

    # Validate files are provided
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
            detail_msg = (
                f"Unsupported audio file type: {f.content_type}. "
                "Please use MP3 or WAV."
            )
            raise HTTPException(status_code=400, detail=detail_msg)

    # Validate speaker image if provided
    if speaker_image:
        if speaker_image.content_type not in [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/webp",
        ]:
            detail_msg = (
                f"Unsupported image file type: {speaker_image.content_type}. "
                "Please use JPEG, PNG, or WebP."
            )
            raise HTTPException(status_code=400, detail=detail_msg)

    # Save audio files to temporary locations
    temp_audio_files_paths = []
    saved_image_path = None
    try:
        # Save uploaded audio files to temporary local paths
        temp_audio_files_paths = save_audio_files_temp(files)

        # Use ElevenLabs SDK to create voice clone
        try:
            cloned_voice_id = elevenlabs_client.create_voice_clone(
                name=name, file_paths=temp_audio_files_paths
            )
        except Exception as e:
            error_msg = f"Error during voice cloning with SDK: {str(e)}"
            raise HTTPException(status_code=500, detail=error_msg)

        # Save speaker image if provided
        if speaker_image:
            try:
                saved_image_path = save_speaker_image(speaker_image, cloned_voice_id)
            except Exception as e:
                # If image save fails, still proceed but log the error
                print(f"Warning: Failed to save speaker image: {e}")
                saved_image_path = None

        # Store in database
        db_voice = VoiceModel(
            voice_id=cloned_voice_id, name=name, image_path=saved_image_path
        )
        db.add(db_voice)
        db.commit()
        db.refresh(db_voice)

        return VoiceCreateResponse(
            voice_id=cloned_voice_id, image_path=saved_image_path
        )

    except Exception as e:
        # Clean up saved image if voice creation failed
        if saved_image_path:
            cleanup_speaker_image(saved_image_path)
        print(f"Error during voice cloning: {e}")
        error_msg = f"An error occurred during voice cloning: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)
    finally:
        # Clean up temporary files
        cleanup_temp_files(temp_audio_files_paths)


@app.post("/voices/{voice_id}/image", response_model=VoiceImageResponse)
async def upload_voice_image(
    voice_id: str,
    speaker_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload or update speaker image for an existing voice clone.
    """
    # Validate speaker image
    if speaker_image.content_type not in [
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    ]:
        detail_msg = (
            f"Unsupported image file type: {speaker_image.content_type}. "
            "Please use JPEG, PNG, or WebP."
        )
        raise HTTPException(status_code=400, detail=detail_msg)

    # Check if voice exists
    db_voice = db.query(VoiceModel).filter(VoiceModel.voice_id == voice_id).first()
    if not db_voice:
        raise HTTPException(status_code=404, detail="Voice not found")

    # Clean up old image if it exists
    old_image_path = db_voice.image_path

    try:
        # Save new speaker image
        new_image_path = save_speaker_image(speaker_image, voice_id)

        # Update database
        db_voice.image_path = new_image_path
        db.commit()

        # Clean up old image after successful update
        if old_image_path and old_image_path != new_image_path:
            cleanup_speaker_image(old_image_path)

        return VoiceImageResponse(
            voice_id=voice_id,
            image_path=new_image_path,
            message="Speaker image uploaded successfully",
        )

    except Exception as e:
        print(f"Error uploading speaker image: {e}")
        error_msg = f"Failed to upload speaker image: {str(e)}"
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/voices", response_model=List[VoiceListResponse])
async def list_voices(db: Session = Depends(get_db)):
    voices = db.query(VoiceModel).all()
    return voices


@app.get("/health")
async def health_check():
    return {"status": "ok"}
