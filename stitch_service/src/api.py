# /home/ubuntu/podcast_workflow_mvp/stitch_service/src/api.py
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os

from .database import get_db
from .stitch_processor import check_stitch_readiness, perform_stitch
from .models import ScriptModel

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Stitch Service")

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
class StitchResponse(BaseModel):
    status: str
    message: str
    total_lines: Optional[int] = None
    completed_lines: Optional[int] = None
    final_video_path: Optional[str] = None


@app.post("/stitch/check/{script_id}", response_model=StitchResponse)
async def check_stitch_status(script_id: int, db: Session = Depends(get_db)):
    """
    Check if a script is ready for stitching.

    This endpoint checks if all lines in a script have completed avatar generation
    and returns the readiness status.
    """
    try:
        result = check_stitch_readiness(db=db, script_id=script_id)

        response = {"status": result.get("status"), "message": result.get("message")}

        if "total_lines" in result:
            response["total_lines"] = result.get("total_lines")

        if "completed_lines" in result:
            response["completed_lines"] = result.get("completed_lines")

        return response

    except Exception as e:
        logger.error(f"Error checking stitch readiness: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stitch/process/{script_id}", response_model=StitchResponse)
async def stitch_script(script_id: int, db: Session = Depends(get_db)):
    """
    Trigger video stitching for a script.

    This endpoint will stitch all video clips for a script into a final video
    if all avatar generation tasks are complete.
    """
    try:
        result = perform_stitch(db=db, script_id=script_id)

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        if result.get("status") in ["not_ready", "already_processed"]:
            # Return appropriate HTTP status for these cases
            status_code = 409 if result.get("status") == "already_processed" else 400
            raise HTTPException(status_code=status_code, detail=result.get("message"))

        response = {"status": result.get("status"), "message": result.get("message")}

        if "final_video_path" in result:
            response["final_video_path"] = result.get("final_video_path")

        if "total_lines" in result:
            response["total_lines"] = result.get("total_lines")

        if "completed_lines" in result:
            response["completed_lines"] = result.get("completed_lines")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during stitching: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/stitch/download/{script_id}", response_class=FileResponse)
async def download_final_video(script_id: int, db: Session = Depends(get_db)):
    """
    Download the final stitched video for a script.

    This endpoint downloads the final stitched video file for a script.
    """
    try:
        script = db.query(ScriptModel).filter(ScriptModel.id == script_id).first()
        if not script or not script.final_video_path:
            raise HTTPException(status_code=404, detail="Final video not found")

        return FileResponse(
            path=script.final_video_path,
            filename=os.path.basename(script.final_video_path),
        )

    except Exception as e:
        logger.error(f"Error downloading final video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
