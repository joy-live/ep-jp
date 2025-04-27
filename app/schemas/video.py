from pydantic import BaseModel, validator
from typing import Optional
from enum import Enum

class VideoStyle(str, Enum):
    ANIME = "Anime"
    REALISTIC = "Realistic"
    THREE_D = "3d"
    CYBERPUNK = "cyberpunk"
    WATERCOLOR = "watercolor"
    OIL_PAINTING = "oil-painting"
    GRAFFITI = "graffiti"
    CARTOON = "Cartoon"

class VideoGenerationRequest(BaseModel):
    prompt: str
    style: Optional[str] = None  # Make style optional
    
    @validator('style')
    def validate_style(cls, v):
        # If style is None or empty, default to "realistic"
        if not v:
            return VideoStyle.REALISTIC.value
            
        # Convert to lowercase for comparison
        v_lower = v.lower()
        
        # Map lowercase values to proper enum values
        style_map = {
            "anime": VideoStyle.ANIME,
            "realistic": VideoStyle.REALISTIC,
            "3d": VideoStyle.THREE_D,
            "cyberpunk": VideoStyle.CYBERPUNK,
            "watercolor": VideoStyle.WATERCOLOR,
            "oil-painting": VideoStyle.OIL_PAINTING,
            "graffiti": VideoStyle.GRAFFITI,
            "cartoon": VideoStyle.CARTOON
        }
        
        if v_lower in style_map:
            return style_map[v_lower].value
        
        # If not found, try direct match with enum values
        for style in VideoStyle:
            if v_lower == style.value.lower():
                return style.value
                
        # If still not found, raise error
        valid_styles = ", ".join([s.value for s in VideoStyle])
        raise ValueError(f"Invalid style. Must be one of: {valid_styles}")

class VideoGenerationResponse(BaseModel):
    video_url: str 