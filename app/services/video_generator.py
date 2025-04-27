import aiohttp
import asyncio
import json
import re
import os
import ssl
import logging
from urllib.parse import urljoin
from datetime import datetime
from typing import Dict, Any, Optional
from app.services.discord_uploader import uploader
from app.schemas.video import VideoGenerationResponse, VideoStyle

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get base URL from environment variables
BASE_URL = os.getenv("VIDEO_SOURCE_URL")

# Styles that need special handling (append to prompt, empty style parameter)
SPECIAL_STYLES = {
    "Cyberpunk",
    "Graffiti", 
    "Oil Painting",
    "Water Color"
}

def create_safe_filename(prompt: str) -> str:
    """Create a safe filename from the prompt with timestamp."""
    # Take first 30 characters of the prompt
    short_prompt = prompt[:30].strip()
    # Clean the filename
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', short_prompt)
    # Add timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_{timestamp}.mp4"

def process_prompt_and_style(prompt: str, style: Optional[str] = None) -> tuple[str, str]:
    """
    Process the prompt and style. For special styles, append style to prompt and use "Realistic" as base style.
    
    Returns:
        tuple[str, str]: (processed_prompt, style_to_use)
    """
    if not style:
        return prompt, "Anime"
        
    # Capitalize first letter of style
    style = style[0].upper() + style[1:] if style else "Anime"
    
    # For special styles, append to prompt and use "Realistic" as base style
    if style in SPECIAL_STYLES:
        return f"{prompt}, {style} style", "Realistic"
        
    # For supported styles (3D, Anime, Realistic), return as is
    return prompt, style

async def generate_video(prompt: str, style: Optional[str] = None) -> VideoGenerationResponse:
    """
    Generate a video using the AI video generation API.
    
    Args:
        prompt: The text prompt describing the video to generate
        style: Optional style parameter. Defaults to "Anime" if not provided.
        
    Returns:
        VideoGenerationResponse containing the video URL
        
    Raises:
        Exception: If video generation fails
    """
    try:
        # Process prompt and style
        processed_prompt, style_to_use = process_prompt_and_style(prompt, style)
        logger.info(f"Using prompt: '{processed_prompt}', style: '{style_to_use}'")
            
        # Create SSL context
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create client session with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            # The API expects exactly these values in this order:
            # [text_prompt, style, "", 8]
            data_array = [
                processed_prompt,  # The processed prompt text
                style_to_use,     # Style parameter (empty for special styles)
                "",              # Empty string parameter
                8                # Number of steps (fixed at 8)
            ]
            
            # Step 1: Join the queue
            payload = {
                "data": data_array,
                "event_data": None,
                "fn_index": 1,
                "session_hash": "-_-",
                "trigger_id": 8
            }
            
            logger.debug(f"Sending payload: {json.dumps(payload, indent=2)}")
            
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "*/*"
            }
            
            async with session.post(
                urljoin(BASE_URL, "/queue/join"),
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Queue join failed: {response.status}, {error_text}")
                    raise Exception(f"Queue join failed: {error_text}")
                    
                queue_data = await response.json()
                event_id = queue_data.get("event_id")
                logger.info(f"Queue join successful, event_id: {event_id}")
                
                if not event_id:
                    logger.error("Failed to get event_id from queue response")
                    raise Exception("Failed to get event_id")
                    
            # Step 2: Poll for results
            params = {
                "session_hash": "-_-"
            }
            
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache"
            }
            
            logger.info(f"Polling for results at {urljoin(BASE_URL, '/queue/data')}")
            async with session.get(
                urljoin(BASE_URL, "/queue/data"),
                params=params,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Data stream failed: {response.status}, {error_text}")
                    raise Exception(f"Data stream failed: {error_text}")
                
                # Read the response as a stream
                video_url = None
                logger.info("Waiting for video generation to complete...")
                async for line in response.content:
                    line = line.decode('utf-8')
                    if not line.strip():
                        continue
                        
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            msg = data.get("msg")
                            logger.info(f"Received message: {msg}")
                            
                            if msg == "process_completed":
                                # Log the full response for debugging
                                logger.debug(f"Process completed response: {json.dumps(data, indent=2)}")
                                
                                # Extract video URL from the response
                                output_data = data.get("output", {}).get("data", [])
                                if output_data and len(output_data) > 0:
                                    first_item = output_data[0]
                                    logger.debug(f"First item in output data: {json.dumps(first_item, indent=2)}")
                                    
                                    # Try different possible structures
                                    if isinstance(first_item, dict):
                                        # Try direct video URL
                                        if "url" in first_item:
                                            video_url = first_item["url"]
                                            logger.info(f"Video URL found directly: {video_url}")
                                            break
                                        
                                        # Try video object
                                        if "video" in first_item:
                                            video_data = first_item["video"]
                                            if isinstance(video_data, dict) and "url" in video_data:
                                                video_url = video_data["url"]
                                                logger.info(f"Video URL found in video object: {video_url}")
                                                break
                                        
                                        # Try nested structure
                                        for key, value in first_item.items():
                                            if isinstance(value, dict) and "url" in value:
                                                video_url = value["url"]
                                                logger.info(f"Video URL found in nested structure: {video_url}")
                                                break
                                    
                                    if not video_url:
                                        logger.debug(f"Could not find video URL in output data: {json.dumps(first_item, indent=2)}")
                                else:
                                    logger.debug("No output data found in response")
                            elif msg == "progress":
                                progress_data = data.get("progress_data", [{}])[0]
                                logger.info(f"Progress: {progress_data.get('progress')}/{progress_data.get('length')} steps")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON: {e}, line: {line}")
                            continue
                
                if video_url:
                    # Download video data
                    logger.info(f"Downloading video from {video_url}")
                    async with session.get(video_url) as video_response:
                        if video_response.status != 200:
                            error_text = await video_response.text()
                            logger.error(f"Failed to download video: {video_response.status}, {error_text}")
                            raise Exception(f"Failed to download video: {error_text}")
                        
                        video_data = await video_response.read()
                        logger.info(f"Video downloaded, size: {len(video_data)} bytes")
                        
                        # Check file size (Discord limit is 25MB)
                        if len(video_data) > 25 * 1024 * 1024:
                            logger.error(f"Video size ({len(video_data)} bytes) exceeds Discord's 25MB limit")
                            raise Exception("Video size exceeds Discord's 25MB limit")
                        
                        # Create a safe filename
                        filename = create_safe_filename(prompt)
                        logger.info(f"Created filename: {filename}")
                        
                        # Upload to Discord
                        logger.info("Uploading video to Discord")
                        discord_url = await uploader.upload_video_from_memory(
                            video_data=video_data,
                            filename=filename,
                            prompt=prompt
                        )
                        
                        if not discord_url:
                            logger.error("Failed to upload video to Discord")
                            raise Exception("Failed to upload video to Discord")
                        
                        logger.info(f"Video uploaded to Discord: {discord_url}")
                        return VideoGenerationResponse(video_url=discord_url)
                else:
                    logger.error("No video URL found in the response")
                    raise Exception("No video URL found in the response")
                    
    except aiohttp.ClientError as e:
        logger.exception(f"Network error during video generation: {str(e)}")
        raise Exception(f"Network error: {str(e)}")
    except json.JSONDecodeError as e:
        logger.exception(f"Invalid JSON response from API: {str(e)}")
        raise Exception("Invalid response from API")
    except Exception as e:
        logger.exception(f"Unexpected error during video generation: {str(e)}")
        raise Exception(f"Failed to generate video: {str(e)}") 