"""Example usage of Game Watcher AI pipeline."""
import logging
from pipeline import GameWatcherPipeline

logging.basicConfig(level=logging.INFO)

def example_youtube():
    """Example: Process a YouTube video."""
    print("Example 1: Processing YouTube Video")
    print("-" * 50)
    
    pipeline = GameWatcherPipeline()
    
    # Replace with actual YouTube URL
    youtube_url = "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
    
    results = pipeline.process(youtube_url, mode="youtube")
    
    print(f"Status: {results.get('status')}")
    print(f"Highlights found: {results.get('summary', {}).get('highlights_found', 0)}")
    print(f"Output file: {results.get('highlight_reel')}")
    print()


def example_upload():
    """Example: Process an uploaded video file."""
    print("Example 2: Processing Uploaded Video")
    print("-" * 50)
    
    pipeline = GameWatcherPipeline()
    
    # Replace with actual file path
    video_path = "path/to/your/video.mp4"
    
    results = pipeline.process(video_path, mode="upload")
    
    print(f"Status: {results.get('status')}")
    if results.get('status') == 'complete':
        print(f"Highlight reel: {results.get('highlight_reel')}")
        print(f"Commentary audio: {results.get('commentary_audio')}")
    print()


def example_live_stream():
    """Example: Process a live stream."""
    print("Example 3: Processing Live Stream")
    print("-" * 50)
    
    pipeline = GameWatcherPipeline()
    
    # Replace with actual stream URL
    stream_url = "rtsp://example.com/stream"
    duration = 60  # seconds
    
    results = pipeline.process_live_stream(stream_url, duration)
    
    print(f"Status: {results.get('status')}")
    print(f"Chunks processed: {results.get('chunks_processed', 0)}")
    print(f"Total detections: {results.get('total_detections', 0)}")
    print()


if __name__ == "__main__":
    print("Game Watcher AI - Example Usage")
    print("=" * 50)
    print()
    
    # Uncomment the example you want to run:
    # example_youtube()
    # example_upload()
    # example_live_stream()
    
    print("\nNote: Update the URLs/paths in the examples before running.")

