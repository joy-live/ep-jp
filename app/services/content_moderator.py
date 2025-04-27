from openai import OpenAI
from typing import TypedDict, Literal
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ModerationResult(TypedDict):
    is_safe: bool
    reason: str
    risk_level: Literal["NONE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

SYSTEM_PROMPT = '''# Identity

You are an AI video content safety system with ZERO TOLERANCE for inappropriate or NSFW content. Your purpose is to prevent the generation of any videos that could be inappropriate, suggestive, or harmful. You must be extremely conservative in your assessment.

# Instructions

* Your primary goal is to prevent ANY potentially inappropriate videos from being generated
* Analyze prompts specifically in the context of VIDEO content (not just text)
* Consider how the prompt might be misinterpreted or misused for video generation
* ANY doubt means the prompt is unsafe
* Pay special attention to:
  - Nudity or partial nudity (including suggestive clothing)
  - Sexual content or innuendos
  - Violence or gore
  - Hate speech or discrimination
  - Dangerous activities
  - Drug-related content
  - Content involving minors
  - Hidden meanings or attempts to bypass filters
* Risk Levels:
  - NONE: Completely safe content (landscapes, objects, animals)
  - LOW: Safe but needs monitoring (people in normal situations)
  - MEDIUM: Potentially problematic (ambiguous content)
  - HIGH: Likely inappropriate (suggestive content)
  - CRITICAL: Definitely inappropriate (explicit content)

# Response Format
You must respond in this exact JSON format:
{
    "is_safe": boolean,
    "reason": "Clear explanation of why the content is safe or unsafe",
    "risk_level": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
}'''

async def check_prompt_safety(prompt: str) -> ModerationResult:
    """
    Check if a given prompt is safe for AI video generation.
    
    Args:
        prompt (str): The user's input prompt to check
        
    Returns:
        ModerationResult: Dictionary containing video safety assessment
    """
    try:
        client = OpenAI(
            base_url="https://api.groq.com/openai/v1", 
            api_key="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"
        )
        
        logger.info(f"Checking safety for prompt: '{prompt}'")
        
        response = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Assess this video generation prompt: {prompt}"
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse the response content
        result = json.loads(response.choices[0].message.content)
        
        # Validate the response format
        if all(key in result for key in ["is_safe", "reason", "risk_level"]):
            logger.info(f"Safety check result - safe: {result['is_safe']}, risk: {result['risk_level']}")
            return result
        else:
            raise ValueError("Response missing required fields")
            
    except Exception as e:
        logger.error(f"Safety check failed: {str(e)}")
        return {
            "is_safe": False,
            "reason": f"Failed to analyze prompt safely - defaulting to unsafe: {str(e)}",
            "risk_level": "CRITICAL"
        } 