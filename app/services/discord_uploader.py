import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from datetime import datetime
import asyncio
from typing import Optional
from io import BytesIO

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '0'))

class DiscordUploader:
    def __init__(self):
        # Initialize bot with required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.channel = None
        self.is_ready = asyncio.Event()
        
        # Set up event handlers
        @self.bot.event
        async def on_ready():
            try:
                self.channel = await self.bot.fetch_channel(CHANNEL_ID)
                self.is_ready.set()
            except Exception as e:
                print(f"Failed to initialize Discord bot: {e}")
                self.is_ready.set()  # Set the event even on failure
    
    async def start(self):
        """Start the Discord bot"""
        if not TOKEN or not CHANNEL_ID:
            raise ValueError("DISCORD_TOKEN and CHANNEL_ID must be set in .env")
            
        try:
            # Start the bot in the background
            asyncio.create_task(self.bot.start(TOKEN))
            # Wait for bot to be ready
            await self.is_ready.wait()
            if not self.channel:
                raise ValueError("Failed to connect to Discord channel")
        except Exception as e:
            raise ValueError(f"Failed to start Discord bot: {e}")

    async def upload_video_from_memory(self, video_data: bytes, filename: str, prompt: str) -> Optional[str]:
        """Upload a video to Discord from memory and return its URL"""
        # Create embed with video info
        embed = discord.Embed(
            title="AI Generated Video",
            description=f"Prompt: {prompt}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="File Name", value=f"`{filename}`", inline=False)
        embed.add_field(name="Size", value=f"{round(len(video_data) / (1024 * 1024), 2)}MB", inline=True)

        # Upload file from memory
        try:
            file = discord.File(BytesIO(video_data), filename=filename)
            message = await self.channel.send(embed=embed, file=file)
            return message.attachments[0].url
        except Exception as e:
            print(f"Failed to upload to Discord: {e}")
            return None

    async def close(self):
        """Close the Discord bot connection"""
        if self.bot:
            await self.bot.close()

# Create a singleton instance
uploader = DiscordUploader() 