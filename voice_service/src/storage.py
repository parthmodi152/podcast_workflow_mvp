import os
import logging
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
        self.bucket_name = "speaker-images"

    def upload_file(
        self, file_content: bytes, file_name: str, content_type: str = "image/jpeg"
    ) -> Optional[str]:
        """
        Upload a file to Supabase Storage
        Returns the public URL if successful, None otherwise
        """
        try:
            # Upload file to bucket
            result = self.supabase.storage.from_(self.bucket_name).upload(
                file_name, file_content, {"content-type": content_type}
            )

            if result:
                # Get public URL
                public_url = self.supabase.storage.from_(
                    self.bucket_name
                ).get_public_url(file_name)
                logger.info(f"Successfully uploaded {file_name} to Supabase Storage")
                return public_url
            else:
                logger.error(f"Failed to upload {file_name}")
                return None

        except Exception as e:
            logger.error(f"Error uploading {file_name} to Supabase: {str(e)}")
            return None

    def delete_file(self, file_name: str) -> bool:
        """
        Delete a file from Supabase Storage
        Returns True if successful, False otherwise
        """
        try:
            result = self.supabase.storage.from_(self.bucket_name).remove([file_name])
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
