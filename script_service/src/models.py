from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

# SQLAlchemy Base
Base = declarative_base()


# SQLAlchemy Models
class ScriptModel(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    length_minutes = Column(Integer, nullable=False)
    format_type = Column(String, nullable=False)  # interview/roundtable
    status = Column(String, default="pending")  # pending/processing/complete
    raw_script_json = Column(Text)  # Stores the full JSON from OpenAI
    questionnaire_json = Column(Text, nullable=True)  # Questionnaire answers
    final_video_path = Column(String, nullable=True)  # Final video path
    lines = relationship("ScriptLineModel", back_populates="script")


class ScriptLineModel(Base):
    __tablename__ = "script_lines"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    speaker_role = Column(String, nullable=False)  # 'host', 'guest', etc.
    speaker_name = Column(String, nullable=False)  # Actual name of the speaker
    text = Column(Text, nullable=False)
    voice_id = Column(String, nullable=True)  # Based on speaker_role
    line_order = Column(Integer, nullable=False)  # To maintain order
    tts_status = Column(String, default="pending")  # TTS status
    audio_file_path = Column(String, nullable=True)  # Audio file path
    avatar_status = Column(String, default="pending")  # Avatar status
    speaker_image_path = Column(String, nullable=True)  # Speaker image
    video_file_path = Column(String, nullable=True)  # Video file path
    avatar_job_id = Column(String, nullable=True)  # Hedra generation job ID
    avatar_asset_id = Column(String, nullable=True)  # Hedra video asset ID
    script = relationship("ScriptModel", back_populates="lines")


# Pydantic Models
class SpeakerInfo(BaseModel):
    role: str  # 'host', 'guest'
    name: str  # Actual name of the speaker
    voice_id: str


class QuestionnaireAnswer(BaseModel):
    question: str
    answer: str


class ScriptCreateRequest(BaseModel):
    title: str
    format_type: Literal["interview", "roundtable", "article"]
    speakers: List[SpeakerInfo]
    length_minutes: int = Field(..., gt=0, le=60)  # Example: 1 to 60 minutes
    questionnaire_answers: List[QuestionnaireAnswer]
    article_url: Optional[str] = None  # For article discussion format


class ScriptLineResponse(BaseModel):
    speaker_role: str
    speaker_name: str
    text: str


class ScriptCreateResponse(BaseModel):
    script_id: int
    title: str
    status: str


class ScriptDetailsResponse(BaseModel):
    script_id: int
    title: str
    format_type: str
    status: str
    length_minutes: int
    lines: List[Dict[str, Any]]
