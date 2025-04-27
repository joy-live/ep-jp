import asyncio
import aiohttp
import json

API_KEY = "az-video-key"
BASE_URL = "http://localhost:8001"

async def test_video_generation() -> None:
    """Test the video generation endpoint and print only the video URL."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Test case with lowercase style
    test_case = {
        "prompt": "pen is in vagin",
        "style": "realistic"  # Using lowercase style
    }
    
    print(f"\nGenerating video with prompt: '{test_case['prompt']}' in {test_case['style']} style")
    
    async with aiohttp.ClientSession() as session:
        try:
            # Make the API request
            async with session.post(
                f"{BASE_URL}/api/v1/generate",
                headers=headers,
                json=test_case
            ) as response:
                # Check response status
                if response.status == 200:
                    result = await response.json()
                    print(f"Video URL: {result['video_url']}")
                else:
                    error = await response.text()
                    print(f"Error: {response.status}")
                    print(f"Details: {error}")
        
        except Exception as e:
            print(f"Request failed: {str(e)}")

async def main() -> None:
    """Run the video generation test."""
    await test_video_generation()

if __name__ == "__main__":
    asyncio.run(main()) 