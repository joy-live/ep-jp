import aiohttp
import logging
import re
from datetime import datetime
from typing import Optional, List
from app.schemas.video import VideoGenerationResponse
from app.services.discord_uploader import uploader
from app.services.video_sources import (
    SahanijiVideoSource,
    KingnishVideoSource,
    ByteDanceVideoSource,
    VideoSourceResponse,
    BaseVideoSource
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_safe_filename(prompt: str) -> str:
    """Create a safe filename from the prompt with timestamp."""
    # Take first 30 characters of the prompt
    short_prompt = prompt[:30].strip()
    # Clean the filename
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', short_prompt)
    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_{timestamp}.mp4"

class VideoGenerator:
    def __init__(self):
        # Initialize video sources in order of preference
        self.sources: List[BaseVideoSource] = [
            ByteDanceVideoSource(),  # Try ByteDance first (best quality)
            KingnishVideoSource(),   # Then Kingnish
            SahanijiVideoSource()    # Finally Sahaniji as last resort
        ]
        
    async def generate_video(self, prompt: str, style: Optional[str] = None) -> VideoGenerationResponse:
        """
        Generate a video using multiple sources. Try each source in sequence until one succeeds.
        Order of attempts:
        1. ByteDance (best quality)
        2. Kingnish (good quality, more style options)
        3. Sahaniji (fallback)
        
        Args:
            prompt: The text prompt describing the video to generate
            style: Optional style parameter
            
        Returns:
            VideoGenerationResponse containing the video URL
            
        Raises:
            Exception: If all video sources fail
        """
        errors = []
        
        # Try each source in sequence
        for source in self.sources:
            try:
                logger.info(f"Attempting video generation with source: {source.__class__.__name__}")
                result = await source.generate_video(prompt, style)
                
                if result.success and result.video_url:
                    # Download and upload to Discord
                    video_url = await self._process_video(result.video_url, prompt)
                    if video_url:
                        return VideoGenerationResponse(video_url=video_url)
                    
                if result.error:
                    errors.append(f"{source.__class__.__name__}: {result.error}")
                
            except Exception as e:
                logger.exception(f"Error with source {source.__class__.__name__}")
                errors.append(f"{source.__class__.__name__}: {str(e)}")
                
        # If we get here, all sources failed
        error_msg = " | ".join(errors)
        raise Exception(f"All video sources failed: {error_msg}")
        
    async def _process_video(self, source_url: str, prompt: str) -> Optional[str]:
        """Download video from source and upload to Discord."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(source_url) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download video: {response.status}")
                        return None
                        
                    video_data = await response.read()
                    
                    # Check file size (Discord limit is 25MB)
                    if len(video_data) > 25 * 1024 * 1024:
                        logger.error(f"Video size ({len(video_data)} bytes) exceeds Discord's 25MB limit")
                        return None
                        
                    # Create filename and upload
                    filename = create_safe_filename(prompt)
                    return await uploader.upload_video_from_memory(
                        video_data=video_data,
                        filename=filename,
                        prompt=prompt
                    )
                    
        except Exception as e:
            logger.exception("Error processing video")
            return None

# Create a singleton instance
generator = VideoGenerator() 