"""Utility functions for video processing."""
from typing import List, Tuple
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import logging
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def sample_key_frames(video_path: str, num_frames: int = 10) -> List[tuple]:
    """
    Sample key frames from video for analysis.
    
    Args:
        video_path: Path to video file
        num_frames: Number of frames to sample
        
    Returns:
        List of tuples: (PIL Image, timestamp_in_seconds, frame_index)
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        if duration == 0:
            cap.release()
            return []
        
        # Sample frames evenly throughout entire video (not just beginning)
        # Use more frames for longer videos
        if duration > 300:  # More than 5 minutes
            num_frames = max(num_frames, int(duration / 30))  # One frame every 30 seconds
        
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        frames = []
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            
            if ret:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                timestamp = idx / fps if fps > 0 else 0
                frames.append((pil_image, timestamp, idx))
        
        cap.release()
        return frames
        
    except Exception as e:
        logger.error(f"Error sampling frames: {e}")
        return []


def get_video_info(video_path: str) -> dict:
    """
    Get video metadata.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dict with video properties
    """
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {}
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        cap.release()
        
        return {
            "width": width,
            "height": height,
            "fps": fps,
            "total_frames": total_frames,
            "duration": duration
        }
        
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {}


def overlay_logo_on_video(
    video_path: Path,
    logo_path: Path,
    position: Tuple[str, str] = ("right", "bottom"),
    scale: float = 0.15,
    margin: int = 30,
) -> Path:
    """
    Overlay a logo image onto a video and return output path. Caches by filename.

    Args:
        video_path: source video
        logo_path: image (preferably PNG with alpha)
        position: (x, y) placement as moviepy positions e.g., ("right","bottom")
        scale: logo width as a fraction of video width
        margin: pixels of margin from edges

    Returns:
        Path to the overlaid output video.
    """
    try:
        # Lazy import to avoid import error crashing the app if moviepy isn't installed
        from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip

        output_dir = OUTPUT_DIR / "generated_videos"
        output_dir.mkdir(parents=True, exist_ok=True)
        out_name = f"{video_path.stem}_with_logo_{abs(hash(str(logo_path))) % 100000}.mp4"
        out_path = output_dir / out_name

        if out_path.exists():
            return out_path

        with VideoFileClip(str(video_path)) as clip:
            vw, vh = clip.size
            logo_img = Image.open(logo_path).convert("RGBA")
            # scale logo by width
            target_w = max(1, int(vw * scale))
            w0, h0 = logo_img.size
            target_h = int(h0 * (target_w / float(w0)))
            logo_img = logo_img.resize((target_w, target_h))
            # save temp png to load as ImageClip
            temp_logo = output_dir / f"_tmp_logo_{abs(hash(str(logo_path))) % 100000}.png"
            logo_img.save(temp_logo)

            # Build image clip with duration
            logo_clip = (ImageClip(str(temp_logo))
                         .set_duration(clip.duration)
                         .margin(right=margin, bottom=margin, opacity=0)
                         .set_pos(position))

            composite = CompositeVideoClip([clip, logo_clip])
            composite.write_videofile(
                str(out_path),
                codec="libx264",
                audio_codec="aac",
                fps=clip.fps or 24,
                preset="medium",
                threads=2,
            )
            # cleanup temp
            try:
                temp_logo.unlink(missing_ok=True)
            except Exception:
                pass
        return out_path
    except Exception as e:
        logger.error(f"Overlay logo failed: {e}")
        return video_path

