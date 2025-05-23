import os
import tempfile
import shutil
from typing import List, Optional
from fastapi import UploadFile

# Environment Variables
MEDIA_DIR = os.getenv("MEDIA_DIR", "/data")
IMAGES_DIR = os.path.join(MEDIA_DIR, "speaker-images")


# Create media directory if it doesn't exist
def ensure_media_directories():
    """Ensure that media directories exist"""
    directories = [MEDIA_DIR, IMAGES_DIR]
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                print(f"Created directory: {directory}")
            except OSError as e:
                print(f"Error creating directory {directory}: {e}")


def save_audio_files_temp(files: List[UploadFile]) -> List[str]:
    """
    Save uploaded audio files to temporary local paths

    Args:
        files: List of uploaded audio files

    Returns:
        List of paths to the saved temporary files
    """
    temp_audio_files_paths = []

    for uploaded_file in files:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(uploaded_file.filename)[1]
        ) as tmp_file:
            shutil.copyfileobj(uploaded_file.file, tmp_file)
            temp_audio_files_paths.append(tmp_file.name)

    return temp_audio_files_paths


def save_speaker_image(image_file: UploadFile, voice_id: str) -> str:
    """
    Save uploaded speaker image to permanent location

    Args:
        image_file: Uploaded image file
        voice_id: Voice ID to use for naming the file

    Returns:
        Full path to the saved image file (for cross-service access)
    """
    # Get file extension from original filename
    file_extension = os.path.splitext(image_file.filename)[1]
    if not file_extension:
        file_extension = ".jpg"  # Default extension

    # Create filename using voice_id
    filename = f"{voice_id}{file_extension}"
    image_path = os.path.join(IMAGES_DIR, filename)

    # Save the image
    with open(image_path, "wb") as f:
        shutil.copyfileobj(image_file.file, f)

    # Return full container path for cross-service access
    return image_path


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files

    Args:
        file_paths: List of paths to temporary files to be deleted
    """
    for path in file_paths:
        if os.path.exists(path):
            os.remove(path)


def cleanup_speaker_image(image_path: Optional[str]) -> None:
    """
    Clean up speaker image file

    Args:
        image_path: Path to the image file to be deleted
    """
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
            print(f"Removed speaker image: {image_path}")
        except OSError as e:
            print(f"Error removing speaker image {image_path}: {e}")
