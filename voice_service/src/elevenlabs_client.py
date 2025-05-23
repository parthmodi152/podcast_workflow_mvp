import os
from io import BytesIO
from typing import List
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment Variables
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")


class ElevenLabsClient:
    """Client for interacting with ElevenLabs voice cloning API"""

    def __init__(self, api_key=None):
        """Initialize the ElevenLabs client with the API key"""
        self.api_key = api_key or ELEVEN_API_KEY
        self.client = ElevenLabs(api_key=self.api_key)

    def create_voice_clone(self, name: str, file_paths: List[str]) -> str:
        """
        Creates a voice clone using the ElevenLabs SDK

        Args:
            name: Name for the cloned voice
            file_paths: List of paths to audio files

        Returns:
            The voice ID of the created clone
        """
        # Open each file as BytesIO object
        files = []
        for file_path in file_paths:
            with open(file_path, "rb") as f:
                files.append(BytesIO(f.read()))

        # Create the voice clone
        voice = self.client.voices.ivc.create(name=name, files=files)

        return voice.voice_id

    def list_voices(self):
        """List all available voices"""
        return self.client.voices.list()
