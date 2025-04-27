from fastapi import APIRouter, HTTPException, Depends
from app.schemas.video import VideoGenerationRequest, VideoGenerationResponse, VideoStyle
from app.services.video_generator import generate_video
from app.services.content_moderator import check_prompt_safety
from app.auth.api_key import get_api_key
import logging
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

# Warning video URL for unsafe content
WARNING_VIDEO_URL = "https://res.cloudinary.com/di3wmppd0/video/upload/v1745719536/1745719517750video_p2olyb.mp4"

# Styles that need to be appended to the prompt
APPEND_STYLE_TO_PROMPT = {
    "Cyberpunk",
    "Graffiti", 
    "Oil Painting",
    "Water Color"
}

def process_prompt_with_style(prompt: str, style: str) -> str:
    """
    Process the prompt based on the style. For certain styles, append the style name to the prompt.
    """
    if style in APPEND_STYLE_TO_PROMPT:
        return f"{prompt}, {style} style"
    return prompt

router = APIRouter()

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video_endpoint(
    request: VideoGenerationRequest,
    api_key: str = Depends(get_api_key)
) -> VideoGenerationResponse:
    try:
        logger.info(f"Received video generation request: prompt='{request.prompt}', style='{request.style}'")
        
        # Check content safety
        safety_result = await check_prompt_safety(request.prompt)
        
        if not safety_result["is_safe"]:
            logger.warning(f"Content safety check failed - Risk Level: {safety_result['risk_level']}, Reason: {safety_result['reason']}")
            # Return warning video instead of raising an error
            return VideoGenerationResponse(video_url=WARNING_VIDEO_URL)
            
        # Process prompt based on style
        processed_prompt = process_prompt_with_style(request.prompt, request.style)
        logger.info(f"Processed prompt: '{processed_prompt}'")
            
        # If content is safe, proceed with video generation
        result = await generate_video(processed_prompt, request.style)
        
        if not result.video_url:
            logger.error("Video generation failed: No video URL returned")
            raise HTTPException(status_code=500, detail="Failed to generate video. Please try again with a different prompt.")
            
        logger.info(f"Video generation successful: {result.video_url}")
        return result
        
    except Exception as e:
        logger.exception(f"Error in video generation endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@router.post("/generate-test", response_model=VideoGenerationResponse)
async def generate_video_test_endpoint(request: VideoGenerationRequest):
    """Test endpoint that returns a pre-generated video URL after a delay."""
    try:
        logger.info(f"Received test video generation request - prompt: '{request.prompt}', style: '{request.style}'")
        
        # Check content safety even for test endpoint
        safety_result = await check_prompt_safety(request.prompt)
        
        if not safety_result["is_safe"]:
            logger.warning(f"Content safety check failed - Risk Level: {safety_result['risk_level']}, Reason: {safety_result['reason']}")
            # Return warning video instead of raising an error
            return VideoGenerationResponse(video_url=WARNING_VIDEO_URL)
        
        # Process prompt based on style
        processed_prompt = process_prompt_with_style(request.prompt, request.style)
        logger.info(f"Processed prompt: '{processed_prompt}'")
        
        # Simulate processing time (3 seconds)
        await asyncio.sleep(3)
        
        # Return a pre-generated Discord video URL
        test_video_url = "https://cdn.discordapp.com/attachments/1365458381896290425/1365685004176330854/A_grandmaster_20250426_134436.mp4?ex=680e34c6&is=680ce346&hm=4e415eaa79b688d9e7b2d1eb798bf427c99bcad06bef429c71bedafe887ae21a&"
        
        logger.info(f"Returning test video URL: {test_video_url}")
        return VideoGenerationResponse(video_url=test_video_url)
        
    except Exception as e:
        logger.error(f"Test video generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 