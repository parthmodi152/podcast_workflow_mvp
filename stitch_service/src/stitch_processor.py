# /home/ubuntu/podcast_workflow_mvp/stitch_service/src/stitch_processor.py
import os
import logging
from sqlalchemy import update, func
from sqlalchemy.orm import Session
from moviepy import VideoFileClip, concatenate_videoclips

from .models import ScriptModel, ScriptLineModel

# Configure logging
logger = logging.getLogger(__name__)

# Environment Variables
MEDIA_VIDEO_DIR = os.getenv("MEDIA_VIDEO_DIR", "/data/podcast-video")
MEDIA_FINAL_DIR = os.getenv("MEDIA_FINAL_DIR", "/data/podcast-final")

# Ensure media directory exists
if not os.path.exists(MEDIA_FINAL_DIR):
    try:
        os.makedirs(MEDIA_FINAL_DIR)
        logger.info(f"Created media directory: {MEDIA_FINAL_DIR}")
    except OSError as e:
        logger.error(f"Could not create directory {MEDIA_FINAL_DIR}: {e}")


def check_stitch_readiness(db: Session, script_id: int) -> dict:
    """
    Check if a script is ready for stitching by verifying all lines are complete.
    Returns a dictionary with status and details.
    """
    logger.info(f"Checking stitch readiness for script_id: {script_id}")

    # Get script details
    script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
    if not script:
        return {"status": "error", "message": f"Script {script_id} not found"}

    # Check if already stitched or in progress
    if script.status in ["complete", "stitching", "stitching_failed"]:
        return {
            "status": "already_processed",
            "message": f"Script {script_id} is already in status: {script.status}",
        }

    # Count total lines vs completed lines
    total_lines = (
        db.query(func.count(ScriptLineModel.id))
        .filter(ScriptLineModel.script_id == script_id)
        .scalar()
    )

    completed_lines = (
        db.query(func.count(ScriptLineModel.id))
        .filter(
            ScriptLineModel.script_id == script_id,
            ScriptLineModel.avatar_status == "complete",
        )
        .scalar()
    )

    logger.info(f"Script {script_id}: {completed_lines}/{total_lines} lines completed")

    if total_lines == 0:
        return {"status": "error", "message": "Script has no lines"}

    if completed_lines < total_lines:
        return {
            "status": "not_ready",
            "message": f"Only {completed_lines}/{total_lines} lines completed",
            "total_lines": total_lines,
            "completed_lines": completed_lines,
        }

    return {
        "status": "ready",
        "message": f"All {total_lines} lines completed and ready for stitching",
        "total_lines": total_lines,
        "completed_lines": completed_lines,
    }


def perform_stitch(db: Session, script_id: int) -> dict:
    """
    Perform the video stitching for a script using MoviePy.
    This preserves all original video properties without modifications.
    """
    logger.info(f"Starting MoviePy stitch process for script_id: {script_id}")

    # First check if ready
    readiness_check = check_stitch_readiness(db, script_id)
    if readiness_check["status"] != "ready":
        return readiness_check

    # Update script status to stitching
    db.execute(
        update(ScriptModel)
        .where(ScriptModel.id == script_id)
        .values(status="stitching")
    )
    db.commit()

    try:
        # Get all video files for the script, ordered by line_order
        lines = (
            db.query(ScriptLineModel)
            .filter(
                ScriptLineModel.script_id == script_id,
                ScriptLineModel.avatar_status == "complete",
                ScriptLineModel.video_file_path.isnot(None),
            )
            .order_by(ScriptLineModel.line_order)
            .all()
        )

        if not lines:
            error_msg = f"No completed video lines found for script {script_id}"
            logger.error(error_msg)

            db.execute(
                update(ScriptModel)
                .where(ScriptModel.id == script_id)
                .values(status="stitching_failed")
            )
            db.commit()

            return {"status": "error", "message": error_msg}

        # Load all video clips
        video_clips = []
        for i, line in enumerate(lines):
            if line.video_file_path and os.path.exists(line.video_file_path):
                logger.info(f"Loading clip {i+1}/{len(lines)}: {line.video_file_path}")
                try:
                    clip = VideoFileClip(line.video_file_path)
                    video_clips.append(clip)
                    logger.info(
                        f"Loaded clip: {line.video_file_path} (duration: {clip.duration:.2f}s)"
                    )
                except Exception as e:
                    error_msg = f"Failed to load video {line.video_file_path}: {str(e)}"
                    logger.error(error_msg)

                    # Clean up any loaded clips
                    for clip in video_clips:
                        clip.close()

                    db.execute(
                        update(ScriptModel)
                        .where(ScriptModel.id == script_id)
                        .values(status="stitching_failed")
                    )
                    db.commit()

                    return {"status": "error", "message": error_msg}
            else:
                error_msg = (
                    f"Video file missing for line {line.id}: {line.video_file_path}"
                )
                logger.error(error_msg)

                # Clean up any loaded clips
                for clip in video_clips:
                    clip.close()

                db.execute(
                    update(ScriptModel)
                    .where(ScriptModel.id == script_id)
                    .values(status="stitching_failed")
                )
                db.commit()

                return {"status": "error", "message": error_msg}

        if not video_clips:
            error_msg = f"No video clips could be loaded for script {script_id}"
            logger.error(error_msg)

            db.execute(
                update(ScriptModel)
                .where(ScriptModel.id == script_id)
                .values(status="stitching_failed")
            )
            db.commit()

            return {"status": "error", "message": error_msg}

        # Prepare output path
        output_episode_path = os.path.join(
            MEDIA_FINAL_DIR, f"{script_id}_final_episode.mp4"
        )

        logger.info(f"Concatenating {len(video_clips)} clips with MoviePy...")

        # Concatenate all clips preserving original properties
        final_clip = concatenate_videoclips(video_clips, method="compose")

        logger.info(f"Writing final video to: {output_episode_path}")

        # Write the final video file
        final_clip.write_videofile(
            output_episode_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
        )

        # Clean up clips to free memory
        final_clip.close()
        for clip in video_clips:
            clip.close()

        logger.info(
            f"Successfully stitched video for script {script_id}: {output_episode_path}"
        )

        # Update script status to complete
        db.execute(
            update(ScriptModel)
            .where(ScriptModel.id == script_id)
            .values(status="complete", final_video_path=output_episode_path)
        )
        db.commit()

        return {
            "status": "complete",
            "message": "Successfully created final video with MoviePy",
            "final_video_path": output_episode_path,
        }

    except Exception as e:
        error_msg = f"Unexpected error during MoviePy stitching: {str(e)}"
        logger.error(error_msg, exc_info=True)

        # Clean up any clips that might still be loaded
        try:
            if "video_clips" in locals():
                for clip in video_clips:
                    clip.close()
            if "final_clip" in locals():
                final_clip.close()
        except:
            pass  # Ignore cleanup errors

        db.execute(
            update(ScriptModel)
            .where(ScriptModel.id == script_id)
            .values(status="stitching_failed")
        )
        db.commit()

        return {"status": "error", "message": error_msg}
