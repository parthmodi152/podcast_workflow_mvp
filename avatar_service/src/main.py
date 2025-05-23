# /home/ubuntu/podcast_workflow_mvp/avatar_service/src/main.py
import logging
import os
from .database import engine
from .models import Base
from .api import app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables if they don't exist
if not os.getenv("SKIP_DB_INIT", False):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created (if they didn't exist)")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

# This is imported by uvicorn when running the app
# Command: uvicorn src.main:app --host 0.0.0.0 --port 8000
