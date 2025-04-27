from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.routers import video_generation
from app.auth.api_key import get_api_key
from app.services.discord_uploader import uploader
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Video Generator",
    description="API for generating videos from text prompts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with authentication
app.include_router(
    video_generation.router,
    prefix="/api/v1",
    tags=["video-generation"],
    dependencies=[Depends(get_api_key)]
)

@app.on_event("startup")
async def startup_event():
    """Initialize Discord bot on startup"""
    await uploader.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Close Discord bot on shutdown"""
    await uploader.close()

@app.get("/")
async def root():
    return {"message": "AI Video Generator API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy"} 