"""Handler for downloading videos from YouTube."""
from pathlib import Path
import logging
from config import UPLOAD_DIR, TEMP_DIR

logger = logging.getLogger(__name__)


class YouTubeHandler:
    """Downloads videos from YouTube using yt-dlp."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or UPLOAD_DIR
        self.output_dir.mkdir(exist_ok=True)
    
    def download(self, url: str, filename: str = None) -> Path:
        """
        Download video from YouTube URL.
        
        Args:
            url: YouTube video URL
            filename: Optional output filename
            
        Returns:
            Path to downloaded video file
        """
        try:
            import yt_dlp
            
            logger.info(f"Downloading YouTube video: {url}")
            
            if not filename:
                filename = "youtube_video"
            
            output_path = self.output_dir / f"{filename}.mp4"
            
            ydl_opts = {
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': str(output_path.with_suffix('')),
                'merge_output_format': 'mp4',
                'quiet': False,
                'no_warnings': False,
                # Add options to bypass 403 errors
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find the actual output file (yt-dlp may save without extension or with different extension)
            # First check if the file exists without extension (yt-dlp sometimes does this)
            no_ext_path = output_path.with_suffix('')
            if no_ext_path.exists():
                # Rename it to have .mp4 extension for consistency
                final_path = no_ext_path.with_suffix('.mp4')
                if not final_path.exists():
                    no_ext_path.rename(final_path)
                return final_path
            
            # Check with expected extension
            if output_path.exists():
                return output_path
            
            # Try to find the file with different extensions
            for ext in ['.mp4', '.mkv', '.webm', '.m4a', '']:
                if ext == '':
                    potential_path = output_path.with_suffix('')
                else:
                    potential_path = output_path.with_suffix(ext)
                if potential_path.exists():
                    # If no extension, rename to .mp4
                    if ext == '':
                        final_path = potential_path.with_suffix('.mp4')
                        potential_path.rename(final_path)
                        return final_path
                    return potential_path
            
            raise FileNotFoundError(f"Downloaded video not found at {output_path}")
            
        except Exception as e:
            logger.error(f"Error downloading YouTube video: {e}")
            raise
    
    def get_video_info(self, url: str) -> dict:
        """Get video metadata without downloading."""
        try:
            import yt_dlp
            
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get("title", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "uploader": info.get("uploader", ""),
                    "thumbnail": info.get("thumbnail", "")
                }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return {}

