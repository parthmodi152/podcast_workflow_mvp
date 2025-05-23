import os
import logging
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)

HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
HEDRA_BASE_URL = "https://api.hedra.com/web-app"


class HedraService:
    """Service class for interacting with Hedra API endpoints"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or HEDRA_API_KEY
        self.base_url = HEDRA_BASE_URL
        self.headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

        # Log API key info (masked for security)
        if self.api_key:
            masked_key = f"{self.api_key[:10]}...{self.api_key[-10:]}"
            logger.info(f"HedraService initialized with API key: {masked_key}")
        else:
            logger.error("HedraService initialized without API key!")

    async def create_asset(self, name: str, asset_type: str) -> Dict[str, Any]:
        """
        Create a new asset in Hedra.

        Args:
            name: Name of the asset
            asset_type: Type of asset ('image', 'audio', 'video', 'voice')

        Returns:
            Dict containing asset info with id for upload
        """
        url = f"{self.base_url}/public/assets"

        payload = {"name": name, "type": asset_type}

        # Log request details
        logger.info(f"Creating asset - URL: {url}")
        logger.info(f"Creating asset - Payload: {payload}")
        logger.info(f"Creating asset - Headers: {self.headers}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=self.headers, json=payload, timeout=30.0
                )

                # Log response details
                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response headers: {dict(response.headers)}")

                if response.status_code != 200:
                    logger.error(f"Response text: {response.text}")

                response.raise_for_status()
                result = response.json()
                logger.info(f"Create asset response: {result}")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Status Error: {e}")
                logger.error(f"Response content: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Request failed: {e}")
                raise

    async def upload_asset(self, asset_id: str, file_path: str) -> Dict[str, Any]:
        """
        Upload file data to an existing asset.

        Args:
            asset_id: ID of the created asset
            file_path: Path to the file to upload

        Returns:
            Dict containing uploaded asset details
        """
        url = f"{self.base_url}/public/assets/{asset_id}/upload"

        # Remove Content-Type header for multipart upload
        upload_headers = {
            key: value for key, value in self.headers.items() if key != "Content-Type"
        }

        # Log request details
        logger.info(f"Uploading asset - URL: {url}")
        logger.info(f"Uploading asset - File: {file_path}")
        logger.info(f"Uploading asset - Headers: {upload_headers}")

        with open(file_path, "rb") as file:
            files = {"file": file}

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        url, headers=upload_headers, files=files, timeout=300.0
                    )

                    # Log response details
                    logger.info(f"Upload response status: {response.status_code}")

                    if response.status_code != 200:
                        logger.error(f"Upload response text: {response.text}")

                    response.raise_for_status()
                    result = response.json()
                    logger.info(f"Upload asset response: {result}")
                    return result

                except httpx.HTTPStatusError as e:
                    logger.error(f"Upload HTTP Status Error: {e}")
                    logger.error(f"Upload response content: {e.response.text}")
                    raise
                except Exception as e:
                    logger.error(f"Upload request failed: {e}")
                    raise

    async def create_and_upload_asset(
        self, file_path: str, asset_type: str, name: str = None
    ) -> Dict[str, Any]:
        """
        Convenience method to create and upload an asset in one call.

        Args:
            file_path: Path to the file to upload
            asset_type: Type of asset ('image', 'audio', 'video', 'voice')
            name: Optional name for the asset (defaults to filename)

        Returns:
            Dict containing uploaded asset details
        """
        if not name:
            name = os.path.basename(file_path)

        logger.info(f"Create and upload asset: {name} ({asset_type}) from {file_path}")

        # Step 1: Create asset
        create_result = await self.create_asset(name, asset_type)
        asset_id = create_result["id"]

        # Step 2: Upload file
        upload_result = await self.upload_asset(asset_id, file_path)

        return upload_result

    async def generate_video(
        self,
        audio_id: str,
        image_id: str = None,
        ai_model_id: str = None,
        text_prompt: str = None,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
    ) -> Dict[str, Any]:
        """
        Generate a video using audio and optionally an image.

        Args:
            audio_id: ID of the uploaded audio asset
            image_id: Optional ID of the uploaded image asset
            ai_model_id: ID of the AI model to use
            text_prompt: Text prompt for video generation
            resolution: Video resolution (default: "720p")
            aspect_ratio: Video aspect ratio (default: "16:9")

        Returns:
            Dict containing generation_id and asset_id
        """
        url = f"{self.base_url}/public/generations"

        if not ai_model_id:
            ai_model_id = "d1dd37a3-e39a-4854-a298-6510289f9cf2"

        if not text_prompt:
            text_prompt = "minimal head movement and expressions"

        payload = {
            "type": "video",
            "ai_model_id": ai_model_id,
            "audio_id": audio_id,
            "generated_video_inputs": {
                "text_prompt": text_prompt,
                "resolution": resolution,
                "aspect_ratio": aspect_ratio,
            },
        }

        if image_id:
            payload["start_keyframe_id"] = image_id

        # Log request details
        logger.info(f"Generate video - URL: {url}")
        logger.info(f"Generate video - Payload: {payload}")
        logger.info(f"Generate video - Headers: {self.headers}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url, headers=self.headers, json=payload, timeout=30.0
                )

                # Log response details
                logger.info(f"Generate video response status: {response.status_code}")

                if response.status_code != 200:
                    logger.error(f"Generate video response text: {response.text}")

                response.raise_for_status()
                result = response.json()
                logger.info(f"Generate video response: {result}")
                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"Generate video HTTP Status Error: {e}")
                logger.error(f"Generate video response content: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Generate video request failed: {e}")
                raise

    async def get_generation_status(self, generation_id: str) -> Dict[str, Any]:
        """
        Check the status of a video generation.

        Args:
            generation_id: ID of the generation to check

        Returns:
            Dict containing status, progress, and url when complete
        """
        url = f"{self.base_url}/public/generations/{generation_id}/status"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def download_video(self, video_url: str, output_path: str) -> str:
        """
        Download a video from a URL to a local file.

        Args:
            video_url: URL of the video to download
            output_path: Local path to save the video

        Returns:
            Path to the downloaded file
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(video_url, timeout=300.0)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

            return output_path
