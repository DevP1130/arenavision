"""Handler for processing live video streams."""
from typing import Iterator, Optional
from pathlib import Path
import logging
import time
import cv2
import numpy as np
from config import TEMP_DIR, CHUNK_DURATION, FRAME_RATE

logger = logging.getLogger(__name__)


class LiveStreamHandler:
    """Handles live video stream processing."""
    
    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or TEMP_DIR
        self.output_dir.mkdir(exist_ok=True)
        self.cap: Optional[cv2.VideoCapture] = None
    
    def connect(self, stream_url: str) -> bool:
        """
        Connect to live stream.
        
        Args:
            stream_url: RTSP, HTTP, or webcam URL
            
        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to stream: {stream_url}")
            self.cap = cv2.VideoCapture(stream_url)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open stream: {stream_url}")
                return False
            
            logger.info("Stream connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to stream: {e}")
            return False
    
    def read_frames(self, num_frames: Optional[int] = None) -> Iterator[np.ndarray]:
        """
        Read frames from live stream.
        
        Args:
            num_frames: Number of frames to read (None for continuous)
            
        Yields:
            Frame arrays
        """
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("Stream not connected. Call connect() first.")
        
        frame_count = 0
        
        while True:
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning("Failed to read frame from stream")
                break
            
            yield frame
            frame_count += 1
            
            if num_frames and frame_count >= num_frames:
                break
    
    def capture_chunk(self, duration: float = None) -> Path:
        """
        Capture a chunk of video from live stream.
        
        Args:
            duration: Duration in seconds (defaults to CHUNK_DURATION)
            
        Returns:
            Path to saved video chunk
        """
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("Stream not connected. Call connect() first.")
        
        duration = duration or CHUNK_DURATION
        fps = FRAME_RATE
        total_frames = int(duration * fps)
        
        # Get video properties
        width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Setup video writer
        output_path = self.output_dir / f"chunk_{int(time.time())}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames_captured = 0
        
        try:
            for frame in self.read_frames(num_frames=total_frames):
                out.write(frame)
                frames_captured += 1
                
                if frames_captured >= total_frames:
                    break
            
            logger.info(f"Captured {frames_captured} frames to {output_path}")
            return output_path
            
        finally:
            out.release()
    
    def process_stream_batch(self, batch_size: int = 10) -> Iterator[Path]:
        """
        Process stream in batches, yielding video chunks.
        
        Args:
            batch_size: Number of chunks to process
            
        Yields:
            Paths to video chunks
        """
        for i in range(batch_size):
            try:
                chunk_path = self.capture_chunk()
                yield chunk_path
            except Exception as e:
                logger.error(f"Error capturing chunk {i}: {e}")
                break
    
    def disconnect(self):
        """Disconnect from stream."""
        if self.cap:
            self.cap.release()
            self.cap = None
            logger.info("Stream disconnected")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

