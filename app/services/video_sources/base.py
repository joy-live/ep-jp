from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoSourceResponse:
    def __init__(self, success: bool, video_url: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.video_url = video_url
        self.error = error

class BaseVideoSource(ABC):
    SUPPORTED_STYLES = ["Anime", "Realistic", "3D"]
    
    def process_style(self, prompt: str, style: Optional[str] = None) -> tuple[str, str]:
        """
        Process the prompt and style. For special styles, append style to prompt and use "Realistic" as base style.
        For supported styles (3D, Anime, Realistic), use them directly.
        """
        if not style:
            return prompt, "Anime"
            
        # Capitalize first letter of style
        style = style[0].upper() + style[1:] if style else "Anime"
        
        # For special styles (anything other than supported styles)
        # append to prompt and use "Realistic" as style
        if style not in self.SUPPORTED_STYLES:
            return f"{prompt}, {style} style", "Realistic"
            
        # For supported styles, return as is
        return prompt, style
    
    @abstractmethod
    async def generate_video(self, prompt: str, style: Optional[str] = None) -> VideoSourceResponse:
        """Generate a video using the source's API"""
        pass 