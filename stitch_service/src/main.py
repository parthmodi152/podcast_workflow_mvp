# /home/ubuntu/podcast_workflow_mvp/stitch_service/src/main.py (or tasks.py)
import os
import subprocess
from celery import Celery
from sqlalchemy import create_engine, update, func, and_
from sqlalchemy.orm import sessionmaker, Session
import logging

from .models import ScriptModel, ScriptLineModel, Base  # Use relative import

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@postgres:5432/podcast_db"
)
MEDIA_VIDEO_DIR = os.getenv(
    "MEDIA_VIDEO_DIR", "/data/podcast-video"
)  # To read individual clips
MEDIA_FINAL_DIR = os.getenv(
    "MEDIA_FINAL_DIR", "/data/podcast-final"
)  # To write final episode
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

if not os.path.exists(MEDIA_FINAL_DIR):
    try:
        os.makedirs(MEDIA_FINAL_DIR)
        logger.info(f"Created media directory: {MEDIA_FINAL_DIR}")
    except OSError as e:
        logger.error(f"Could not create media directory {MEDIA_FINAL_DIR}: {e}")

# Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Celery Application
celery_app = Celery(
    "stitch_service_worker",
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
    name="stitch_service.tasks.enqueue_stitch_job",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def enqueue_stitch_job(self, completed_line_id: int):
    logger.info(
        f"Received stitch enqueue request for completed line_id: {completed_line_id}"
    )
    db: Session = get_db_session()
    try:
        # Find the script_id for the completed line
        line = (
            db.query(ScriptLineModel)
            .filter(ScriptLineModel.id == completed_line_id)
            .first()
        )
        if not line:
            logger.error(
                f"Line with id {completed_line_id} not found. Cannot check script for stitching."
            )
            return  # Or raise an error

        script_id = line.script_id
        logger.info(
            f"Checking script {script_id} for stitch readiness after line {completed_line_id} completion."
        )

        # Check if all lines for this script have avatar_status = "complete"
        total_lines_count = (
            db.query(func.count(ScriptLineModel.id))
            .filter(ScriptLineModel.script_id == script_id)
            .scalar()
        )
        completed_lines_count = (
            db.query(func.count(ScriptLineModel.id))
            .filter(
                ScriptLineModel.script_id == script_id,
                ScriptLineModel.avatar_status == "complete",
            )
            .scalar()
        )

        logger.info(
            f"Script {script_id}: Total lines = {total_lines_count}, Completed avatar lines = {completed_lines_count}"
        )

        if total_lines_count == completed_lines_count and total_lines_count > 0:
            # Check if the script is not already stitched or being stitched
            script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
            if script and script.status not in [
                "complete",
                "stitching_failed",
                "stitching",
            ]:
                logger.info(
                    f"All lines for script {script_id} are complete. Dispatching actual stitch task."
                )
                # Update script status to "stitching"
                db.execute(
                    update(ScriptModel)
                    .where(ScriptModel.id == script_id)
                    .values(status="stitching")
                )
                db.commit()
                # Dispatch the actual stitching task
                perform_stitch_for_script.delay(script_id)
            elif script:
                logger.info(
                    f"Script {script_id} is already in status '{script.status}'. No new stitch task dispatched."
                )
            else:
                logger.error(f"Script {script_id} not found for stitching check.")
        else:
            logger.info(
                f"Script {script_id} not yet ready for stitching. {completed_lines_count}/{total_lines_count} lines ready."
            )

    except Exception as exc:
        logger.error(
            f"Error in enqueue_stitch_job for line {completed_line_id}: {exc}",
            exc_info=True,
        )
        self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    name="stitch_service.tasks.perform_stitch_for_script",
    bind=True,
    max_retries=2,
    default_retry_delay=180,
)
def perform_stitch_for_script(self, script_id: int):
    logger.info(f"Starting stitch process for script_id: {script_id}")
    db: Session = get_db_session()
    list_file_path = None  # To ensure cleanup

    try:
        # 1. Fetch all video file paths for the script, ordered by line_order
        lines = (
            db.query(ScriptLineModel)
            .filter(
                ScriptLineModel.script_id == script_id,
                ScriptLineModel.avatar_status == "complete",  # Double check
                ScriptLineModel.video_file_path.isnot(None),  # Ensure path exists
            )
            .order_by(ScriptLineModel.line_order)
            .all()
        )

        if not lines:
            logger.error(
                f"No completed video lines found for script {script_id}. Cannot stitch."
            )
            db.execute(
                update(ScriptModel)
                .where(ScriptModel.id == script_id)
                .values(status="stitching_failed")
            )
            db.commit()
            return

        video_files = []
        for line in lines:
            if line.video_file_path and os.path.exists(line.video_file_path):
                video_files.append(line.video_file_path)
            else:
                logger.error(
                    f"Video file path missing or file not found for line {line.id} ({line.video_file_path}). Cannot stitch script {script_id}."
                )
                db.execute(
                    update(ScriptModel)
                    .where(ScriptModel.id == script_id)
                    .values(status="stitching_failed")
                )
                db.commit()
                return

        if not video_files:
            logger.error(
                f"No valid video files collected for script {script_id}. Cannot stitch."
            )
            db.execute(
                update(ScriptModel)
                .where(ScriptModel.id == script_id)
                .values(status="stitching_failed")
            )
            db.commit()
            return

        # 2. Create list.txt for FFmpeg
        # Ensure this path is unique if multiple stitches can happen concurrently, or clean up well.
        # For simplicity, using script_id in the filename within a temp/data location for the service.
        list_file_path = os.path.join(
            MEDIA_FINAL_DIR, f"list_{script_id}.txt"
        )  # Store temp list file here or in a dedicated temp dir
        with open(list_file_path, "w") as f:
            for video_file in video_files:
                # FFmpeg concat demuxer needs specific format: file 'relative/path/to/file.mp4'
                # Ensure paths are correctly formatted for FFmpeg, especially if they contain spaces or special chars.
                # For -safe 0, absolute paths should be fine.
                f.write(f"file '{video_file}'\n")  # Quote paths for safety
        logger.info(
            f"Created FFmpeg list file: {list_file_path} for script {script_id}"
        )

        # 3. Execute FFmpeg command
        output_episode_path = os.path.join(
            MEDIA_FINAL_DIR, f"{script_id}_final_episode.mp4"
        )
        ffmpeg_command = [
            "ffmpeg",
            "-y",  # Overwrite output file if it exists
            "-f",
            "concat",
            "-safe",
            "0",  # Allows unsafe file paths (e.g. absolute paths)
            "-i",
            list_file_path,
            "-c",
            "copy",  # Copies codecs, much faster if clips are compatible
            output_episode_path,
        ]

        logger.info(
            f"Executing FFmpeg for script {script_id}: {' '.join(ffmpeg_command)}"
        )
        process = subprocess.Popen(
            ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            logger.error(
                f"FFmpeg failed for script {script_id}. Return code: {process.returncode}"
            )
            logger.error(f"FFmpeg stdout: {stdout.decode(errors='ignore')}")
            logger.error(f"FFmpeg stderr: {stderr.decode(errors='ignore')}")
            db.execute(
                update(ScriptModel)
                .where(ScriptModel.id == script_id)
                .values(status="stitching_failed")
            )
            db.commit()
            raise Exception(
                f"FFmpeg concatenation failed for script {script_id}. Error: {stderr.decode(errors='ignore')}"
            )

        logger.info(
            f"FFmpeg successfully stitched video for script {script_id} to {output_episode_path}"
        )

        # 4. Update script status to "complete"
        db.execute(
            update(ScriptModel)
            .where(ScriptModel.id == script_id)
            .values(status="complete")
        )
        db.commit()
        logger.info(
            f"Script {script_id} status updated to complete. Final episode at: {output_episode_path}"
        )

    except Exception as exc:
        logger.error(
            f"Error during stitch process for script {script_id}: {exc}", exc_info=True
        )
        db.execute(
            update(ScriptModel)
            .where(ScriptModel.id == script_id)
            .values(status="stitching_failed")
        )
        db.commit()
        self.retry(exc=exc)
    finally:
        if list_file_path and os.path.exists(list_file_path):
            try:
                os.remove(list_file_path)
                logger.info(f"Cleaned up list file: {list_file_path}")
            except OSError as e:
                logger.error(f"Error cleaning up list file {list_file_path}: {e}")
        db.close()


# To run this worker (example, adjust for your setup):
# celery -A stitch_service.src.main worker -l info -Q stitch_queue
