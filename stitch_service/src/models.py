# /home/ubuntu/podcast_workflow_mvp/stitch_service/src/models.py
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class ScriptModel(Base):
    __tablename__ = "scripts"
    # Mirrored from script_service.src.main.py
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    length_minutes = Column(Integer)
    format_type = Column(String, nullable=True)
    status = Column(String, default="pending")  # Status during stitching
    raw_script_json = Column(Text)
    questionnaire_json = Column(Text, nullable=True)
    # For storing the final video path
    final_video_path = Column(String, nullable=True)
    lines = relationship("ScriptLineModel", back_populates="script")


class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    # Mirrored from other services
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    speaker_role = Column(String)
    speaker_name = Column(String, nullable=True)
    text = Column(Text)
    voice_id = Column(String)
    line_order = Column(Integer)
    tts_status = Column(String, nullable=True)
    audio_file_path = Column(String, nullable=True)
    avatar_status = Column(String, default="pending")
    video_file_path = Column(String, nullable=True)  # Path to generated video
    speaker_image_path = Column(String, nullable=True)
    avatar_job_id = Column(String, nullable=True)  # Hedra generation job ID
    avatar_asset_id = Column(String, nullable=True)  # Hedra video asset ID
    script = relationship("ScriptModel", back_populates="lines")
