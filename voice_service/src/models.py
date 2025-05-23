from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from typing import Optional

# SQLAlchemy Base
Base = declarative_base()


# SQLAlchemy Models
class VoiceModel(Base):
    __tablename__ = "voices"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    voice_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    image_path = Column(String, nullable=True)  # Path to speaker image


# Pydantic Models
class VoiceCreateResponse(BaseModel):
    voice_id: str
    image_path: Optional[str] = None


class VoiceListResponse(BaseModel):
    id: int
    voice_id: str
    name: str
    image_path: Optional[str] = None


class VoiceImageResponse(BaseModel):
    voice_id: str
    image_path: str
    message: str
