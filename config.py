"""Configuration management for Game Watcher AI."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "outputs")
TEMP_DIR = BASE_DIR / os.getenv("TEMP_DIR", "temp")

# Create directories if they don't exist
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Video Processing
MAX_VIDEO_DURATION = 3600  # 1 hour in seconds
FRAME_RATE = 30
CHUNK_DURATION = 10  # seconds per chunk for live processing

# Agent Configuration
ENABLE_VEO_EDITING = True
ENABLE_COMMENTARY = True
HIGHLIGHT_MIN_DURATION = 3  # minimum highlight length in seconds
HIGHLIGHT_MAX_DURATION = 30  # maximum highlight length in seconds

