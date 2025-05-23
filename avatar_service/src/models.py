# /home/ubuntu/podcast_workflow_mvp/avatar_service/src/models.py
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from .database import Base


class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    # Mirrored from script_service.src.main.py & tts_service.src.models.py
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(
        Integer, ForeignKey("scripts.id")
    )  # Assuming scripts table exists
    speaker_role = Column(String, nullable=True)  # Added for reference
    speaker_name = Column(String, nullable=True)  # Added for reference
    text = Column(Text, nullable=True)  # Added for reference
    line_order = Column(Integer, nullable=True)  # Added for reference
    # Fields used by avatar service
    tts_status = Column(String, nullable=True)  # Status from previous step
    audio_file_path = Column(String, nullable=True)  # Path to the audio
    speaker_image_path = Column(String, nullable=True)  # Path to speaker image
    avatar_status = Column(
        String, default="pending"
    )  # pending, processing, complete, failed
    video_file_path = Column(String, nullable=True)  # Path to the generated video
    # For tracking job status
    avatar_job_id = Column(String, nullable=True)  # ID of the Hedra generation job
    avatar_asset_id = Column(String, nullable=True)  # ID of the Hedra video asset


# We might need to access ScriptModel to check when all lines of a script are done for stitching,
# but stitch_service will likely handle that. For now, avatar_service focuses on individual lines.
