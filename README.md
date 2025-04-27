# Video AI API

A FastAPI-based service for generating AI videos from text prompts with style customization.

## Features

- Text-to-video generation with multiple style options
- Content safety moderation
- Discord integration for video storage
- Docker and Docker Compose support
- Health monitoring
- API key authentication
- CORS support

## Supported Styles

- Realistic
- Anime
- 3D
- Cyberpunk (with style prompt)
- Graffiti (with style prompt)
- Oil Painting (with style prompt)
- Water Color (with style prompt)

## Environment Variables

```env
DISCORD_TOKEN=your_discord_token
CHANNEL_ID=your_channel_id
API_KEY=your_api_key
```

## Running with Docker Compose

```bash
docker-compose up --build
```

## API Endpoints

- `POST /api/v1/generate`: Generate video from prompt
- `POST /api/v1/generate-test`: Test endpoint with pre-generated video
- `GET /health`: Health check endpoint 