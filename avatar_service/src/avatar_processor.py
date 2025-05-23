# /home/ubuntu/podcast_workflow_mvp/avatar_service/src/avatar_processor.py
import os
import logging
from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import ScriptLineModel
from .hedra_service import HedraService

# Configure logging
logger = logging.getLogger(__name__)

# Environment Variables
HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
MEDIA_AUDIO_DIR = os.getenv("MEDIA_AUDIO_DIR", "/data/podcast-audio")
MEDIA_VIDEO_DIR = os.getenv("MEDIA_VIDEO_DIR", "/data/podcast-video")

# Ensure media directory exists
if not os.path.exists(MEDIA_VIDEO_DIR):
    try:
        os.makedirs(MEDIA_VIDEO_DIR)
        logger.info(f"Created media directory: {MEDIA_VIDEO_DIR}")
    except OSError as e:
        logger.error(f"Could not create directory {MEDIA_VIDEO_DIR}: {e}")


async def process_avatar_generation(db: Session, line_id: int) -> dict:
    """
    Start the avatar generation process for a script line.
    Returns a dictionary with job_id and status.
    """
    logger.info(f"Starting avatar generation for line_id: {line_id}")

    # Get the script line
    script_line = (
        db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()
    )

    if not script_line:
        logger.error(f"Script line with id {line_id} not found")
        return {"status": "error", "message": f"Script line {line_id} not found"}

    if not script_line.audio_file_path:
        logger.error(f"No audio file path for line {line_id}")
        return {"status": "error", "message": "No audio file path available"}

    if not os.path.exists(script_line.audio_file_path):
        logger.error(f"Audio file {script_line.audio_file_path} not found")
        return {"status": "error", "message": "Audio file not found"}

    if not HEDRA_API_KEY:
        logger.error("HEDRA_API_KEY not configured")
        return {"status": "error", "message": "HEDRA_API_KEY not configured"}

    # Update status to processing
    db.execute(
        update(ScriptLineModel)
        .where(ScriptLineModel.id == line_id)
        .values(avatar_status="processing")
    )
    db.commit()

    try:
        # Initialize Hedra service
        hedra_service = HedraService(api_key=HEDRA_API_KEY)

        # Step 1: Upload audio file
        logger.info(f"Uploading audio for line {line_id}")
        audio_filename = os.path.basename(script_line.audio_file_path)
        audio_asset = await hedra_service.create_and_upload_asset(
            script_line.audio_file_path, "audio", audio_filename
        )
        audio_id = audio_asset["id"]

        # Step 2: Upload portrait image if available
        image_id = None

        # Debug logging for image path
        logger.info(f"Checking speaker image for line {line_id}")
        logger.info(f"speaker_image_path: {script_line.speaker_image_path}")

        if script_line.speaker_image_path:
            logger.info(f"Speaker image path exists: {script_line.speaker_image_path}")
            logger.info(
                f"Checking if file exists at path: {script_line.speaker_image_path}"
            )

            if os.path.exists(script_line.speaker_image_path):
                logger.info(f"File exists! Uploading portrait for line {line_id}")
                image_filename = os.path.basename(script_line.speaker_image_path)
                image_asset = await hedra_service.create_and_upload_asset(
                    script_line.speaker_image_path, "image", image_filename
                )
                image_id = image_asset["id"]
                logger.info(f"Image uploaded successfully with ID: {image_id}")
            else:
                logger.error(
                    f"Speaker image file does not exist: {script_line.speaker_image_path}"
                )
        else:
            logger.warning(f"No speaker_image_path set for line {line_id}")

        logger.info(f"Final image_id for video generation: {image_id}")

        # Step 3: Generate video
        logger.info(f"Creating video generation for line {line_id}")
        generation_response = await hedra_service.generate_video(
            audio_id=audio_id, image_id=image_id
        )

        generation_id = generation_response["id"]
        asset_id = generation_response["asset_id"]

        # Store generation ID in database
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_job_id=generation_id, avatar_asset_id=asset_id)
        )
        db.commit()

        logger.info(
            f"Avatar generation job started with generation_id: " f"{generation_id}"
        )
        return {
            "status": "processing",
            "generation_id": generation_id,
            "asset_id": asset_id,
            "message": "Avatar generation job started",
        }

    except Exception as e:
        logger.error(f"Error starting avatar generation: {str(e)}")
        db.execute(
            update(ScriptLineModel)
            .where(ScriptLineModel.id == line_id)
            .values(avatar_status="failed")
        )
        db.commit()
        return {"status": "error", "message": str(e)}


async def check_avatar_status(db: Session, line_id: int) -> dict:
    """
    Check the status of an avatar generation job and update the database
    if completed.
    """
    logger.info(f"Checking status for line_id: {line_id}")

    # Get the script line
    script_line = (
        db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()
    )

    if not script_line:
        logger.error(f"Script line with id {line_id} not found")
        return {"status": "error", "message": f"Script line {line_id} not found"}

    if not script_line.avatar_job_id:
        logger.error(f"No generation ID for line {line_id}")
        return {"status": "error", "message": "No avatar generation ID"}

    if script_line.avatar_status == "complete":
        return {
            "status": "complete",
            "message": "Avatar generation already completed",
            "video_path": script_line.video_file_path,
        }

    if script_line.avatar_status == "failed":
        return {"status": "failed", "message": "Avatar generation failed"}

    try:
        # Initialize Hedra service
        hedra_service = HedraService(api_key=HEDRA_API_KEY)

        # Check generation status
        status_response = await hedra_service.get_generation_status(
            script_line.avatar_job_id
        )

        status = status_response["status"]
        progress = status_response["progress"]

        if status == "complete":
            # Download the video
            video_output_path = os.path.join(MEDIA_VIDEO_DIR, f"{line_id}.mp4")
            video_url = status_response["url"]

            await hedra_service.download_video(video_url, video_output_path)

            # Update database
            db.execute(
                update(ScriptLineModel)
                .where(ScriptLineModel.id == line_id)
                .values(avatar_status="complete", video_file_path=video_output_path)
            )
            db.commit()

            logger.info(f"Avatar generation completed for line {line_id}")
            return {
                "status": "complete",
                "message": "Avatar generation completed",
                "video_path": video_output_path,
            }

        elif status == "error":
            error_message = status_response.get("error_message", "Unknown error")

            # Update database
            db.execute(
                update(ScriptLineModel)
                .where(ScriptLineModel.id == line_id)
                .values(avatar_status="failed")
            )
            db.commit()

            logger.error(
                f"Avatar generation failed for line {line_id}: " f"{error_message}"
            )
            return {"status": "failed", "message": error_message}

        else:
            # Still processing (queued, pending, processing, finalizing)
            progress_percent = progress * 100
            return {
                "status": "processing",
                "progress": progress,
                "message": (f"Avatar generation in progress: {progress_percent:.0f}%"),
            }

    except Exception as e:
        logger.error(f"Error checking avatar status: {str(e)}")
        return {"status": "error", "message": str(e)}
