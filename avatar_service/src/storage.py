import os
import logging
import httpx
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


class SupabaseStorage:
    def __init__(self):
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.audio_bucket = "podcast-audio"
        self.video_bucket = "podcast-video"

    def download_file(self, bucket_name: str, public_url: str) -> Optional[bytes]:
        """Download a file from Supabase Storage URL"""
        try:
            response = httpx.get(public_url)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(
                    f"Failed to download from {public_url}: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"Error downloading from {public_url}: {str(e)}")
            return None

    def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        bucket_name: str = "podcast-video",
        content_type: str = "video/mp4",
    ) -> Optional[str]:
        """
        Upload a file to Supabase Storage
        Returns the public URL if successful, None otherwise
        """
        try:
            # Upload file to bucket
            result = self.supabase.storage.from_(bucket_name).upload(
                file_name, file_content, {"content-type": content_type}
            )

            if result:
                # Get public URL
                public_url = self.supabase.storage.from_(bucket_name).get_public_url(
                    file_name
                )
                logger.info(f"Successfully uploaded {file_name} to Supabase Storage")
                return public_url
            else:
                logger.error(f"Failed to upload {file_name}")
                return None

        except Exception as e:
            logger.error(f"Error uploading {file_name} to Supabase: {str(e)}")
            return None

    def delete_file(self, file_name: str, bucket_name: str = "podcast-video") -> bool:
        """
        Delete a file from Supabase Storage
        Returns True if successful, False otherwise
        """
        try:
            result = self.supabase.storage.from_(bucket_name).remove([file_name])
            if result:
                logger.info(f"Successfully deleted {file_name} from Supabase Storage")
                return True
            else:
                logger.error(f"Failed to delete {file_name}")
                return False

        except Exception as e:
            logger.error(f"Error deleting {file_name} from Supabase: {str(e)}")
            return False


# Global storage instance
storage = None


def get_storage() -> SupabaseStorage:
    """Get or create the storage instance"""
    global storage
    if storage is None:
        storage = SupabaseStorage()
    return storage
