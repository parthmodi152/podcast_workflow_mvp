# /home/ubuntu/podcast_workflow_mvp/tts_service/src/main.py
import os
from celery import Celery
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, Session
import logging

# ElevenLabs SDK
from elevenlabs.client import ElevenLabs  # Using synchronous client for Celery tasks

# Assuming models.py is in the same directory or accessible in PYTHONPATH
from .models import ScriptLineModel, VoiceModel, Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/podcast_db"
)
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
MEDIA_DIR = os.getenv("MEDIA_DIR", "/data/podcast-audio")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

if not ELEVEN_API_KEY:
    logger.error("ELEVEN_API_KEY is not set. TTS generation will fail.")
if not os.path.exists(MEDIA_DIR):
    try:
        os.makedirs(MEDIA_DIR)
        logger.info(f"Created media directory: {MEDIA_DIR}")
    except OSError as e:
        logger.error(f"Could not create media directory {MEDIA_DIR}: {e}")

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

celery_app = Celery(
    "tts_service_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.main"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


def get_db_session():
    return SessionLocal()


@celery_app.task(
    name="src.main.generate_tts_for_line",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_tts_for_line(self, line_id: int, voice_id: str, text: str):
    logger.info(
        f"Received TTS task for line_id: {line_id}, voice_id: {voice_id} using SDK"
    )
    db: Session = get_db_session()

    try:
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(tts_status="processing")
        )
        db.commit()

        if not ELEVEN_API_KEY:
            raise ValueError("ELEVEN_API_KEY not configured for TTS service.")

        client = ElevenLabs(api_key=ELEVEN_API_KEY)
        audio_file_path = os.path.join(MEDIA_DIR, f"{line_id}.mp3")

        # Use ElevenLabs SDK to convert text to speech and stream
        audio_stream = client.text_to_speech.convert_as_stream(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",  # As per previous instructions
            output_format="mp3_44100_128",  # As per previous instructions
        )

        with open(audio_file_path, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)
        logger.info(f"Audio for line {line_id} saved to {audio_file_path} using SDK")

        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(tts_status="complete", audio_file_path=audio_file_path)
        )
        db.commit()
        logger.info(
            f"Line {line_id} status updated to complete, audio path: {audio_file_path}"
        )

        voice_record = (
            db.query(VoiceModel).filter(VoiceModel.voice_id == voice_id).first()
        )
        speaker_image_path = None  # Changed from speaker_image_url
        if voice_record and voice_record.image_path:
            speaker_image_path = voice_record.image_path
        else:
            logger.warning(
                f"Speaker image path not found for voice_id {voice_id}. Avatar generation for line {line_id} might be affected or use a default."
            )
            # speaker_image_path remains None, avatar_service should handle this

        celery_app.send_task(
            "src.main.generate_avatar_for_line",
            args=[line_id, speaker_image_path, audio_file_path],
            queue="avatar_queue",
        )
        logger.info(
            f"Dispatched avatar generation task for line {line_id} with image_path {speaker_image_path}"
        )

    except Exception as exc:
        logger.error(
            f"Error during TTS for line {line_id} with SDK: {exc}", exc_info=True
        )
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(tts_status="failed")
        )
        db.commit()
        self.retry(exc=exc)
    finally:
        db.close()
