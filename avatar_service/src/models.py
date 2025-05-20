# /home/ubuntu/podcast_workflow_mvp/avatar_service/src/models.py
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    # Mirrored from script_service.src.main.py & tts_service.src.models.py
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id")) # Assuming scripts table exists
    # speaker_role = Column(String) # Not directly used by avatar service for its own logic
    # text = Column(Text) # Not directly used
    # voice_id = Column(String) # Not directly used
    # line_order = Column(Integer) # Not directly used
    # tts_status = Column(String) # Status from previous step
    audio_file_path = Column(String, nullable=True) # Path to the generated audio from TTS service
    avatar_status = Column(String, default="pending") # e.g., pending, processing, complete, failed
    video_file_path = Column(String, nullable=True) # Path to the generated video

# We might need to access ScriptModel to check when all lines of a script are done for stitching,
# but stitch_service will likely handle that. For now, avatar_service focuses on individual lines.

