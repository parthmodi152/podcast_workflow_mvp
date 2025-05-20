# /home/ubuntu/podcast_workflow_mvp/tts_service/src/models.py
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    # Mirrored from script_service.src.main.py
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id")) # Assuming scripts table exists
    speaker_role = Column(String)
    text = Column(Text)
    voice_id = Column(String)
    line_order = Column(Integer)
    tts_status = Column(String, default="pending") # e.g., pending, processing, complete, failed
    audio_file_path = Column(String, nullable=True) # Path to the generated audio
    # Fields for avatar and stitch service might also be here if this service updates them, or in their own models
    avatar_status = Column(String, default="pending")
    video_file_path = Column(String, nullable=True)

class VoiceModel(Base):
    __tablename__ = "voices"
    # Mirrored from voice_service.src.main.py
    id = Column(Integer, primary_key=True, index=True)
    voice_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    image_path = Column(String, nullable=True) # Changed from image_url to image_path

