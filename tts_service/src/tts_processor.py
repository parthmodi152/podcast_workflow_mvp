# /home/ubuntu/podcast_workflow_mvp/tts_service/src/tts_processor.py
import os
import logging
from sqlalchemy import update
from sqlalchemy.orm import Session
from elevenlabs.client import ElevenLabs

from .models import ScriptLineModel, VoiceModel
from .storage import get_storage

# Configure logging
logger = logging.getLogger(__name__)

# Environment Variables
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")


def process_line_tts(db: Session, line_id: int, voice_id: str, text: str) -> bool:
    """Process TTS for a single line synchronously"""
    logger.info(f"Processing TTS for line_id: {line_id}, voice_id: {voice_id}")

    try:
        # Update line status to processing
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(tts_status="processing")
        )
        db.commit()

        if not ELEVEN_API_KEY:
            raise ValueError("ELEVEN_API_KEY not configured for TTS service.")

        client = ElevenLabs(api_key=ELEVEN_API_KEY)

        # Use ElevenLabs SDK to convert text to speech and stream
        audio_stream = client.text_to_speech.stream(
            text=text, voice_id=voice_id, model_id="eleven_multilingual_v2"
        )

        # Collect audio data
        audio_data = bytearray()
        for chunk in audio_stream:
            if isinstance(chunk, bytes):
                audio_data.extend(chunk)

        # Upload to Supabase Storage
        filename = f"{line_id}.mp3"
        storage = get_storage()
        public_url = storage.upload_file(bytes(audio_data), filename, "audio/mpeg")

        if not public_url:
            raise Exception("Failed to upload audio to Supabase Storage")

        logger.info(f"Audio for line {line_id} uploaded to Supabase: {filename}")

        # Update line status to complete
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(tts_status="complete", audio_file_path=public_url)
        )
        db.commit()

        # Get speaker image if available
        voice_record = (
            db.query(VoiceModel).filter(VoiceModel.voice_id == voice_id).first()
        )
        speaker_image_path = None
        if voice_record and voice_record.image_path:
            speaker_image_path = voice_record.image_path

        # Mark as ready for avatar generation
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(
                avatar_status="ready_for_processing",
                speaker_image_path=speaker_image_path,
            )
        )
        db.commit()
        logger.info(f"Line {line_id} marked ready for avatar generation")

        return True
    except Exception as e:
        logger.error(f"Error during TTS processing for line {line_id}: {e}")
        # Update line status to failed
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(tts_status="failed")
        )
        db.commit()
        return False
