# /home/ubuntu/podcast_workflow_mvp/avatar_service/src/api.py
import logging
from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import asyncio

from .database import get_db
from .models import ScriptLineModel
from .avatar_processor import process_avatar_generation, check_avatar_status

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Avatar Service")

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
class AvatarResponse(BaseModel):
    status: str
    message: str
    job_id: Optional[str] = None
    progress: Optional[float] = None
    video_path: Optional[str] = None


@app.post("/avatar/generate/{line_id}", response_model=AvatarResponse)
async def generate_avatar(line_id: int, db: Session = Depends(get_db)):
    """
    Start the avatar generation process for a script line.

    This endpoint will trigger the avatar generation process but will not
    wait for completion. The job will run asynchronously.
    """
    try:
        result = await process_avatar_generation(db=db, line_id=line_id)

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return {
            "status": result.get("status"),
            "message": result.get("message"),
            "job_id": result.get("job_id"),
        }

    except Exception as e:
        logger.error(f"Error in generate_avatar endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/avatar/status/{line_id}", response_model=AvatarResponse)
async def get_avatar_status(line_id: int, db: Session = Depends(get_db)):
    """
    Check the status of an avatar generation job.

    This endpoint will check the current status of the avatar generation process
    and return information about progress or completion.
    """
    try:
        result = await check_avatar_status(db=db, line_id=line_id)

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        response = {
            "status": result.get("status"),
            "message": result.get("message"),
        }

        if "job_id" in result:
            response["job_id"] = result.get("job_id")

        if "progress" in result:
            response["progress"] = result.get("progress")

        if "video_path" in result:
            response["video_path"] = result.get("video_path")

        return response

    except Exception as e:
        logger.error(f"Error in get_avatar_status endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/avatar/video/{line_id}")
async def get_line_video(line_id: int, db: Session = Depends(get_db)):
    """Serve video file for a specific line"""
    line = db.query(ScriptLineModel).filter(ScriptLineModel.id == line_id).first()

    if not line:
        raise HTTPException(status_code=404, detail=f"Line {line_id} not found")

    if not line.video_file_path or not os.path.exists(line.video_file_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        line.video_file_path, media_type="video/mp4", filename=f"line_{line_id}.mp4"
    )


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/avatar/sync-stuck-jobs")
async def sync_stuck_jobs(db: Session = Depends(get_db)):
    """
    Manually sync stuck jobs that are in 'processing' status.

    This endpoint checks all lines in 'processing' status and updates
    their status by checking with the Hedra API.
    """
    try:
        # Find all lines stuck in processing
        stuck_lines = (
            db.query(ScriptLineModel)
            .filter(
                ScriptLineModel.avatar_status == "processing",
                ScriptLineModel.avatar_job_id.isnot(None),
            )
            .all()
        )

        if not stuck_lines:
            return {
                "status": "success",
                "message": "No stuck jobs found",
                "processed": 0,
                "updated": 0,
            }

        updated_count = 0
        error_count = 0

        for line in stuck_lines:
            try:
                logger.info(f"Checking stuck line {line.id}")
                result = await check_avatar_status(db=db, line_id=line.id)

                if result.get("status") in ["complete", "failed"]:
                    updated_count += 1
                    logger.info(
                        f"Updated line {line.id} status to {result.get('status')}"
                    )
                else:
                    logger.info(f"Line {line.id} still processing")

            except Exception as e:
                error_count += 1
                logger.error(f"Error checking line {line.id}: {str(e)}")

        return {
            "status": "success",
            "message": f"Sync completed. {updated_count} lines updated, {error_count} errors",
            "processed": len(stuck_lines),
            "updated": updated_count,
            "errors": error_count,
        }

    except Exception as e:
        logger.error(f"Error in sync_stuck_jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task to sync stuck jobs
async def background_sync_task():
    """Background task that periodically checks and syncs stuck jobs."""
    while True:
        try:
            await asyncio.sleep(300)  # Wait 5 minutes between checks

            # Import here to avoid circular imports
            from .database import SessionLocal

            db = SessionLocal()
            try:
                # Find stuck lines
                stuck_lines = (
                    db.query(ScriptLineModel)
                    .filter(
                        ScriptLineModel.avatar_status == "processing",
                        ScriptLineModel.avatar_job_id.isnot(None),
                    )
                    .all()
                )

                if stuck_lines:
                    logger.info(
                        f"Background sync: Found {len(stuck_lines)} stuck jobs, checking..."
                    )

                    for line in stuck_lines:
                        try:
                            result = await check_avatar_status(db=db, line_id=line.id)
                            if result.get("status") in ["complete", "failed"]:
                                logger.info(
                                    f"Background sync: Updated line {line.id} to {result.get('status')}"
                                )
                        except Exception as e:
                            logger.error(
                                f"Background sync: Error checking line {line.id}: {str(e)}"
                            )

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Background sync task error: {str(e)}")


@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup."""
    logger.info("Starting background sync task...")
    asyncio.create_task(background_sync_task())
