import aiohttp
import json
import os
from typing import Optional
from .base import BaseVideoSource, VideoSourceResponse, logger

class KingnishVideoSource(BaseVideoSource):
    def __init__(self):
        self.base_url = os.getenv("KINGNISH_VIDEO_URL")
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/?__theme=system"
        }
        
    async def generate_video(self, prompt: str, style: Optional[str] = None) -> VideoSourceResponse:
        try:
            # Process prompt and style
            processed_prompt, style_to_use = self.process_style(prompt, style)
            logger.info(f"[Kingnish] Using prompt: '{processed_prompt}', style: '{style_to_use}'")
            
            # Prepare the payload
            payload = {
                "data": [
                    processed_prompt,
                    style_to_use,
                    "",  # Motion model parameter (must be empty for this API)
                    8  # Number of frames
                ],
                "event_data": None,
                "fn_index": 0,
                "session_hash": "session_" + str(hash(prompt))[:8],
                "trigger_id": 1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/run/predict",
                    headers=self.headers,
                    json=payload,
                    params={"__theme": "system"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Kingnish] API request failed: {response.status}, {error_text}")
                        return VideoSourceResponse(success=False, error=f"API request failed with status code: {response.status}")
                    
                    result = await response.json()
                    
                    # Extract video URL from response
                    if result.get("data") and result["data"][0].get("video"):
                        video_data = result["data"][0]["video"]
                        return VideoSourceResponse(success=True, video_url=video_data["url"])
                    else:
                        logger.error("[Kingnish] No video data in response")
                        return VideoSourceResponse(success=False, error="No video data in response")
                        
        except Exception as e:
            logger.exception(f"[Kingnish] Error during video generation: {str(e)}")
            return VideoSourceResponse(success=False, error=str(e)) 