# /home/ubuntu/podcast_workflow_mvp/avatar_service/src/main.py
import os
import httpx  # Keep for downloading the final video if SDK provides URL
import time
from celery import Celery
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, Session
import logging
import asyncio  # For asyncio.sleep

# Hedra SDK Imports
from hedra import AsyncHedra  # Use AsyncHedra as the task is async
from hedra.types import (
    CharacterCreateParams,
    AvatarProjectItem,
    AudioCreateParams,
    PortraitCreateParams,
    AudioCreateResponse,
    PortraitCreateResponse,
)

from .models import ScriptLineModel, Base  # Use relative import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/podcast_db"
)
HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
MEDIA_AUDIO_DIR = os.getenv("MEDIA_AUDIO_DIR", "/data/podcast-audio")  # To read audio
MEDIA_VIDEO_DIR = os.getenv("MEDIA_VIDEO_DIR", "/data/podcast-video")  # To write video
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

if not HEDRA_API_KEY:
    logger.error("HEDRA_API_KEY is not set. Avatar generation will fail.")

# Create media directories if they don_t exist
for dir_path in [MEDIA_VIDEO_DIR]:
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            logger.info(f"Created directory: {dir_path}")
        except OSError as e:
            logger.error(f"Could not create directory {dir_path}: {e}")

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Celery Application
celery_app = Celery(
    "avatar_service_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["src.main"],  # Fix path to match new Celery startup command
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
    name="src.main.generate_avatar_for_line",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
)
async def generate_avatar_for_line(
    self, line_id: int, speaker_image_path: str | None, audio_file_path: str
):
    logger.info(
        f"Received avatar task for line_id: {line_id}, image_path: {speaker_image_path}, audio_path: {audio_file_path}"
    )
    db: Session = get_db_session()
    hedra_client = AsyncHedra(api_key=HEDRA_API_KEY)
    sdk_voice_url = None
    sdk_avatar_image_url = None

    try:
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_status="processing")
        )
        db.commit()

        if not HEDRA_API_KEY:
            raise ValueError("HEDRA_API_KEY not configured for avatar service.")
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(
                f"Audio file {audio_file_path} not found for line {line_id}"
            )

        # Step 1: Upload audio file using Hedra SDK
        logger.info(
            f"Uploading audio {audio_file_path} for line {line_id} using Hedra SDK."
        )
        with open(audio_file_path, "rb") as audio_file:
            audio_params: AudioCreateParams = {"file": audio_file}
            audio_upload_response: AudioCreateResponse = (
                await hedra_client.audio.create(**audio_params)
            )
            sdk_voice_url = audio_upload_response.url
        logger.info(
            f"Hedra SDK audio upload successful for line {line_id}, voice_url: {sdk_voice_url}"
        )

        # Step 2: Upload speaker image file using Hedra SDK (if path is provided)
        if speaker_image_path and os.path.exists(speaker_image_path):
            logger.info(
                f"Uploading image {speaker_image_path} for line {line_id} using Hedra SDK."
            )
            with open(speaker_image_path, "rb") as image_file:
                # Assuming default aspect ratio or one that matches typical podcast video needs
                portrait_params: PortraitCreateParams = {
                    "file": image_file,
                    "aspect_ratio": "16:9",
                }
                portrait_upload_response: PortraitCreateResponse = (
                    await hedra_client.portraits.create(**portrait_params)
                )
                sdk_avatar_image_url = portrait_upload_response.url
            logger.info(
                f"Hedra SDK portrait upload successful for line {line_id}, avatar_image_url: {sdk_avatar_image_url}"
            )
        elif speaker_image_path:  # Path provided but file doesn't exist
            logger.warning(
                f"Speaker image file {speaker_image_path} not found for line {line_id}. Proceeding without custom avatar image."
            )
        else:  # No path provided
            logger.info(
                f"No speaker image path provided for line {line_id}. Proceeding without custom avatar image (Hedra might use a default or require one)."
            )
            # If Hedra requires an avatar_image, this path would lead to an error.
            # The CharacterCreateParams suggests avatar_image is Optional.

        video_output_path = os.path.join(MEDIA_VIDEO_DIR, f"{line_id}.mp4")

        # Step 3: Create Character using Hedra SDK
        logger.info(
            f"Requesting Hedra character generation for line {line_id} using SDK."
        )
        character_params: CharacterCreateParams = {
            "audio_source": "audio",
            "voice_url": sdk_voice_url,
        }
        if sdk_avatar_image_url:
            character_params["avatar_image"] = sdk_avatar_image_url
        # Default aspect_ratio if not set by portrait, or ensure it's consistent.
        # The SDK snippet for CharacterCreateParams has aspect_ratio, let's set it here too.
        character_params["aspect_ratio"] = "16:9"

        create_response = await hedra_client.characters.create(**character_params)
        job_id = create_response.job_id
        logger.info(
            f"Hedra SDK job_id: {job_id} for line {line_id}. Polling for completion..."
        )

        # Step 4: Poll for completion using Hedra SDK
        polling_attempts = 0
        max_polling_attempts = 60
        poll_interval = 10
        final_video_url = None

        while polling_attempts < max_polling_attempts:
            await asyncio.sleep(poll_interval)
            project_item: AvatarProjectItem = await hedra_client.projects.retrieve(
                project_id=job_id
            )
            status = project_item.status
            logger.info(
                f"Polling Hedra project {job_id} for line {line_id} (SDK): status = {status}, progress = {project_item.progress}"
            )

            if status == "done":
                final_video_url = project_item.video_url
                break
            elif status == "failed":
                error_message = (
                    project_item.error_message or "Unknown Hedra processing error (SDK)"
                )
                raise Exception(
                    f"Hedra video generation failed for project {job_id} (SDK): {error_message}"
                )
            polling_attempts += 1

        if not final_video_url:
            raise TimeoutError(
                f"Hedra video generation timed out for project {job_id} (SDK) after {max_polling_attempts * poll_interval} seconds."
            )

        # Step 5: Download the video
        logger.info(
            f"Downloading generated video from {final_video_url} for line {line_id}."
        )
        async with httpx.AsyncClient() as http_client:
            video_response = await http_client.get(final_video_url, timeout=300.0)
            video_response.raise_for_status()
            with open(video_output_path, "wb") as f:
                f.write(video_response.content)
        logger.info(f"Video for line {line_id} saved to {video_output_path}")

        # Update DB
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_status="complete", video_file_path=video_output_path)
        )
        db.commit()
        logger.info(f"Line {line_id} avatar status updated to complete.")

        celery_app.send_task(
            "src.main.enqueue_stitch_job", args=[line_id], queue="stitch_queue"
        )
        logger.info(f"Dispatched stitch enqueue task for line {line_id}")

    except httpx.HTTPStatusError as exc:
        logger.error(
            f"HTTP error during video download for line {line_id}: {exc.response.status_code} - {exc.response.text}",
            exc_info=True,
        )
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_status="failed")
        )
        db.commit()
        self.retry(exc=exc)
    except FileNotFoundError as exc:
        logger.error(
            f"File not found during avatar generation for line {line_id}: {exc}",
            exc_info=True,
        )
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_status="failed")
        )
        db.commit()
        # Do not retry for FileNotFoundError as it's a persistent issue with inputs
    except Exception as exc:
        logger.error(
            f"Unexpected error during avatar generation for line {line_id} (SDK): {exc}",
            exc_info=True,
        )
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_status="failed")
        )
        db.commit()
        self.retry(exc=exc)
    finally:
        db.close()
