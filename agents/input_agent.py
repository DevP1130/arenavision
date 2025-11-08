"""Input Agent - handles video input from YouTube or live streams."""
from typing import Optional, Union
from pathlib import Path
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class InputAgent(BaseAgent):
    """Handles video input from multiple sources."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("InputAgent", config)
        self.mode: Optional[str] = None
        self.video_path: Optional[Path] = None
    
    def process(self, input_data: Union[str, Path]) -> dict:
        """
        Process video input.
        
        Args:
            input_data: YouTube URL, file path, or stream URL
            
        Returns:
            dict with video_path, mode, and metadata
        """
        input_str = str(input_data)
        
        # Detect input type
        if input_str.startswith(("http://", "https://")):
            if "youtube.com" in input_str or "youtu.be" in input_str:
                self.mode = "youtube"
                return self._handle_youtube(input_str)
            elif input_str.startswith("rtsp://") or "stream" in input_str.lower():
                self.mode = "live"
                return self._handle_live_stream(input_str)
            else:
                raise ValueError(f"Unsupported URL format: {input_str}")
        else:
            # File path
            self.mode = "upload"
            return self._handle_file_upload(Path(input_str))
    
    def _handle_youtube(self, url: str) -> dict:
        """Download video from YouTube."""
        self.log("Downloading YouTube video", "info")
        
        try:
            from handlers.youtube_handler import YouTubeHandler
            handler = YouTubeHandler()
            video_path = handler.download(url)
            self.video_path = video_path
            
            return {
                "video_path": str(video_path),
                "mode": "youtube",
                "source": url,
                "status": "downloaded"
            }
        except Exception as e:
            self.log(f"Error downloading YouTube video: {e}", "error")
            raise
    
    def _handle_file_upload(self, file_path: Path) -> dict:
        """Handle uploaded video file."""
        self.log(f"Processing uploaded file: {file_path}", "info")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")
        
        self.video_path = file_path
        
        return {
            "video_path": str(file_path),
            "mode": "upload",
            "source": str(file_path),
            "status": "ready"
        }
    
    def _handle_live_stream(self, stream_url: str) -> dict:
        """Handle live stream input."""
        self.log(f"Setting up live stream: {stream_url}", "info")
        
        return {
            "video_path": None,
            "mode": "live",
            "source": stream_url,
            "status": "streaming"
        }

