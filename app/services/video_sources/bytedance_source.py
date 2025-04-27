import aiohttp
import json
import os
import asyncio
from typing import Optional
from .base import BaseVideoSource, VideoSourceResponse, logger

class ByteDanceVideoSource(BaseVideoSource):
    def __init__(self):
        self.base_url = os.getenv("BYTEDANCE_VIDEO_URL")
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/?__theme=system"
        }
        
    async def _join_queue(self, prompt: str, session: aiohttp.ClientSession, num_frames: int = 8) -> Optional[str]:
        """Join the generation queue and get an event_id"""
        payload = {
            "data": [prompt, "epiCRealism", "", num_frames],
            "event_data": None,
            "fn_index": 1,
            "session_hash": "session_" + str(hash(prompt))[:8],
            "trigger_id": 1
        }

        try:
            async with session.post(
                f"{self.base_url}/queue/join",
                headers=self.headers,
                json=payload,
                params={"__theme": "system"}
            ) as response:
                if response.status != 200:
                    return None
                    
                result = await response.json()
                return result.get("event_id")
                
        except Exception as e:
            logger.error(f"[ByteDance] Failed to join queue: {str(e)}")
            return None
            
    async def _poll_queue(self, session: aiohttp.ClientSession, session_hash: str, timeout: int = 60) -> VideoSourceResponse:
        """Poll the queue for results with SSE streaming"""
        start_time = asyncio.get_event_loop().time()
        params = {"session_hash": session_hash}
        
        try:
            async with session.get(
                f"{self.base_url}/queue/data",
                headers={"Accept": "text/event-stream"},
                params=params
            ) as response:
                if response.status != 200:
                    return VideoSourceResponse(success=False, error="Failed to connect to queue data stream")
                    
                async for line in response.content:
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        return VideoSourceResponse(success=False, error="Generation timed out")
                        
                    line = line.decode('utf-8')
                    if not line.strip() or not line.startswith('data: '):
                        continue
                        
                    try:
                        data = json.loads(line[6:])  # Skip "data: " prefix
                        msg = data.get("msg")
                        
                        if msg == "process_completed":
                            if data.get("success", False) and data.get("output", {}).get("data"):
                                video_data = data["output"]["data"][0]["video"]
                                return VideoSourceResponse(success=True, video_url=video_data["url"])
                            else:
                                return VideoSourceResponse(success=False, error="Generation failed")
                                
                        elif msg == "error":
                            return VideoSourceResponse(success=False, error=str(data.get("error", "Unknown error")))
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"[ByteDance] Failed to parse JSON: {str(e)}")
                        continue
                        
        except Exception as e:
            return VideoSourceResponse(success=False, error=f"Error while polling queue: {str(e)}")
            
    async def generate_video(self, prompt: str, style: Optional[str] = None) -> VideoSourceResponse:
        """
        Generate a video using the ByteDance AnimateDiff Lightning API.
        Since this source doesn't support styles directly, we append the style to the prompt.
        """
        try:
            # Process prompt and style - style will be appended to prompt
            processed_prompt, _ = self.process_style(prompt, style)
            logger.info(f"[ByteDance] Using prompt: '{processed_prompt}'")
            
            session_hash = "session_" + str(hash(processed_prompt))[:8]
            
            async with aiohttp.ClientSession() as session:
                # Join the queue
                event_id = await self._join_queue(processed_prompt, session)
                if not event_id:
                    return VideoSourceResponse(success=False, error="Failed to join generation queue")
                
                # Poll for results
                return await self._poll_queue(session, session_hash)
                
        except Exception as e:
            logger.exception(f"[ByteDance] Error during video generation: {str(e)}")
            return VideoSourceResponse(success=False, error=str(e)) 