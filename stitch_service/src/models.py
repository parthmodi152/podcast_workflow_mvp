# /home/ubuntu/podcast_workflow_mvp/stitch_service/src/models.py
from sqlalchemy import Column, String, Integer, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ScriptModel(Base):
    __tablename__ = "scripts"
    # Mirrored from script_service.src.main.py
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    length_minutes = Column(Integer)
    status = Column(String, default="pending") # This will be updated to "complete"
    raw_script_json = Column(Text)
    lines = relationship("ScriptLineModel", back_populates="script")

class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    # Mirrored from other services
    id = Column(Integer, primary_key=True, index=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    speaker_role = Column(String)
    text = Column(Text)
    voice_id = Column(String)
    line_order = Column(Integer)
    tts_status = Column(String)
    audio_file_path = Column(String, nullable=True)
    avatar_status = Column(String, default="pending")
    video_file_path = Column(String, nullable=True) # Path to the generated video from avatar_service
    script = relationship("ScriptModel", back_populates="lines")

