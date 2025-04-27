import aiohttp
import json
import ssl
import os
from typing import Optional
from urllib.parse import urljoin
from .base import BaseVideoSource, VideoSourceResponse, logger

class SahanijiVideoSource(BaseVideoSource):
    def __init__(self):
        self.base_url = os.getenv("SAHANIJI_VIDEO_URL")
        
    async def generate_video(self, prompt: str, style: Optional[str] = None) -> VideoSourceResponse:
        try:
            # Process prompt and style
            processed_prompt, style_to_use = self.process_style(prompt, style)
            logger.info(f"[Sahaniji] Using prompt: '{processed_prompt}', style: '{style_to_use}'")
            
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
                    style_to_use,     # Style parameter
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
                
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "*/*"
                }
                
                # Join queue
                async with session.post(
                    urljoin(self.base_url, "/queue/join"),
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"[Sahaniji] Queue join failed: {response.status}, {error_text}")
                        return VideoSourceResponse(success=False, error=f"Queue join failed: {error_text}")
                        
                    queue_data = await response.json()
                    event_id = queue_data.get("event_id")
                    
                    if not event_id:
                        logger.error("[Sahaniji] Failed to get event_id from queue response")
                        return VideoSourceResponse(success=False, error="Failed to get event_id")
                    
                # Step 2: Poll for results
                params = {"session_hash": "-_-"}
                headers = {
                    "Accept": "text/event-stream",
                    "Cache-Control": "no-cache"
                }
                
                async with session.get(
                    urljoin(self.base_url, "/queue/data"),
                    params=params,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return VideoSourceResponse(success=False, error=f"Data stream failed: {error_text}")
                    
                    # Read the response as a stream
                    video_url = None
                    async for line in response.content:
                        line = line.decode('utf-8')
                        if not line.strip() or not line.startswith('data: '):
                            continue
                            
                        try:
                            data = json.loads(line[6:])
                            msg = data.get("msg")
                            
                            if msg == "process_completed":
                                output_data = data.get("output", {}).get("data", [])
                                if output_data and len(output_data) > 0:
                                    first_item = output_data[0]
                                    
                                    # Try different possible structures
                                    if isinstance(first_item, dict):
                                        if "url" in first_item:
                                            video_url = first_item["url"]
                                            break
                                        elif "video" in first_item and isinstance(first_item["video"], dict):
                                            video_url = first_item["video"].get("url")
                                            if video_url:
                                                break
                                                
                        except json.JSONDecodeError as e:
                            logger.error(f"[Sahaniji] Failed to parse JSON: {e}")
                            continue
                    
                    if video_url:
                        return VideoSourceResponse(success=True, video_url=video_url)
                    else:
                        return VideoSourceResponse(success=False, error="No video URL found in the response")
                        
        except Exception as e:
            logger.exception(f"[Sahaniji] Error during video generation: {str(e)}")
            return VideoSourceResponse(success=False, error=str(e)) 