import os
import tempfile
import shutil
from typing import List, Optional
from fastapi import UploadFile
from .storage import get_storage

# Environment Variables (keeping for backward compatibility)
MEDIA_DIR = os.getenv("MEDIA_DIR", "/data")
IMAGES_DIR = os.path.join(MEDIA_DIR, "speaker-images")


# Create media directory if it doesn't exist (for local temp files only)
def ensure_media_directories():
    """Ensure that temporary media directories exist"""
    # Only create temp directory now since images go to Supabase
    temp_dir = tempfile.gettempdir()
    if not os.path.exists(temp_dir):
        try:
            os.makedirs(temp_dir)
            print(f"Created temp directory: {temp_dir}")
        except OSError as e:
            print(f"Error creating temp directory {temp_dir}: {e}")


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


def save_speaker_image(image_file: UploadFile, voice_id: str) -> Optional[str]:
    """
    Save uploaded speaker image to Supabase Storage

    Args:
        image_file: Uploaded image file
        voice_id: Voice ID to use for naming the file

    Returns:
        Public URL to the saved image file, or None if failed
    """
    try:
        # Get file extension from original filename
        file_extension = os.path.splitext(image_file.filename)[1]
        if not file_extension:
            file_extension = ".jpg"  # Default extension

        # Create filename using voice_id
        filename = f"{voice_id}{file_extension}"

        # Read file content
        image_file.file.seek(0)  # Ensure we're at the start
        file_content = image_file.file.read()

        # Determine content type
        content_type = image_file.content_type or "image/jpeg"

        # Upload to Supabase Storage
        storage = get_storage()
        public_url = storage.upload_file(file_content, filename, content_type)

        if public_url:
            print(f"Successfully uploaded speaker image: {filename}")
            return public_url
        else:
            print(f"Failed to upload speaker image: {filename}")
            return None

    except Exception as e:
        print(f"Error saving speaker image: {str(e)}")
        return None


def cleanup_temp_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files

    Args:
        file_paths: List of paths to temporary files to be deleted
    """
    for path in file_paths:
        if os.path.exists(path):
            os.remove(path)


def cleanup_speaker_image(image_url: Optional[str]) -> None:
    """
    Clean up speaker image from Supabase Storage

    Args:
        image_url: Public URL of the image to be deleted
    """
    if not image_url:
        return

    try:
        # Extract filename from URL
        # URL format: https://xxx.supabase.co/storage/v1/object/public/
        # speaker-images/filename
        filename = image_url.split("/")[-1]

        # Delete from Supabase Storage
        storage = get_storage()
        success = storage.delete_file(filename)

        if success:
            print(f"Removed speaker image: {filename}")
        else:
            print(f"Failed to remove speaker image: {filename}")

    except Exception as e:
        print(f"Error removing speaker image {image_url}: {e}")
