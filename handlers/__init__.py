"""Input handlers for different video sources."""
from .youtube_handler import YouTubeHandler
from .live_stream_handler import LiveStreamHandler

__all__ = ["YouTubeHandler", "LiveStreamHandler"]

