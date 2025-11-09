"""Video editing utilities for applying chatbot instructions."""
from typing import Dict, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def apply_editing_instructions(
    video_path: str,
    instructions: Dict,
    segments: List[Dict] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Apply editing instructions to video.
    
    Args:
        video_path: Path to source video
        instructions: Editing instructions from chatbot
        segments: List of segments (if editing segments)
        output_path: Output path (auto-generated if None)
        
    Returns:
        Path to edited video
    """
    try:
        from moviepy import VideoFileClip, concatenate_videoclips
        from config import OUTPUT_DIR, TRANSITION_DURATION
        
        if output_path is None:
            iteration_num = len(list(OUTPUT_DIR.glob("highlight_reel_iteration_*.mp4"))) + 1
            output_path = str(OUTPUT_DIR / f"highlight_reel_iteration_{iteration_num:03d}.mp4")
        
        action = instructions.get("action", "edit_highlight_reel")
        target = instructions.get("target", "highlight_reel")
        params = instructions.get("parameters", {})
        
        source_video = VideoFileClip(video_path)
        
        if action == "edit_highlight_reel":
            # Edit the full highlight reel
            edited_clip = source_video
            
            # Apply speed changes
            speed = params.get("speed", "normal")
            if speed == "slow_motion":
                # Slow motion: use fx method if available, otherwise skip
                if hasattr(edited_clip, 'fx') and hasattr(edited_clip.fx, 'speedx'):
                    edited_clip = edited_clip.fx.speedx(0.5)
                elif hasattr(edited_clip, 'set_fps'):
                    # Alternative: change fps to simulate slow motion
                    original_fps = edited_clip.fps
                    edited_clip = edited_clip.set_fps(original_fps * 0.5)
                    edited_clip = edited_clip.set_duration(edited_clip.duration * 2)
                else:
                    logger.warning("Slow motion not supported in this MoviePy version")
            elif speed == "fast_forward":
                # Fast forward: use fx method if available
                if hasattr(edited_clip, 'fx') and hasattr(edited_clip.fx, 'speedx'):
                    edited_clip = edited_clip.fx.speedx(2.0)
                elif hasattr(edited_clip, 'set_fps'):
                    # Alternative: change fps to simulate fast forward
                    original_fps = edited_clip.fps
                    edited_clip = edited_clip.set_fps(original_fps * 2)
                    edited_clip = edited_clip.set_duration(edited_clip.duration * 0.5)
                else:
                    logger.warning("Fast forward not supported in this MoviePy version")
            
            # Apply trimming
            trim_start = params.get("trim_start")
            trim_end = params.get("trim_end")
            if trim_start is not None or trim_end is not None:
                start = trim_start if trim_start is not None else 0
                end = trim_end if trim_end is not None else edited_clip.duration
                edited_clip = edited_clip.subclipped(start, end)
            
            # Write edited video
            edited_clip.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=30
            )
            edited_clip.close()
            source_video.close()
            
        elif action == "edit_segment" and segments:
            # Edit specific segments
            focus_segments = params.get("focus_segments", [])
            remove_segments = params.get("remove_segments", [])
            modify_segments = params.get("modify_segments", [])
            
            logger.info(f"Editing segments: remove_segments={remove_segments}, focus_segments={focus_segments}, modify_segments={modify_segments}, total_segments={len(segments)}")
            
            # Create a map of segment modifications
            segment_modifications = {}
            for mod in modify_segments:
                seg_idx = mod.get("index")
                if seg_idx is not None:
                    segment_modifications[seg_idx] = {
                        "trim_start": mod.get("trim_start"),
                        "trim_end": mod.get("trim_end")
                    }
                    logger.info(f"Segment {seg_idx} will be modified: trim_start={mod.get('trim_start')}, trim_end={mod.get('trim_end')}")
            
            # Filter segments
            filtered_segments = []
            for i, segment in enumerate(segments):
                # Skip if in remove list
                if i in remove_segments:
                    logger.info(f"Skipping segment {i} (marked for removal)")
                    continue
                # Skip if focus list exists and this segment is not in it
                if focus_segments and i not in focus_segments:
                    logger.info(f"Skipping segment {i} (not in focus list)")
                    continue
                filtered_segments.append(segment)
                logger.info(f"Including segment {i}: {segment.get('start_time', 0):.1f}s-{segment.get('end_time', 0):.1f}s")
            
            # Extract and concatenate filtered segments with modifications
            clips = []
            for i, segment in enumerate(filtered_segments):
                # Find original segment index
                original_idx = segments.index(segment)
                
                start = segment.get("start_time", 0)
                end = segment.get("end_time", start + 10)
                
                # Apply modifications if this segment is in the modifications map
                if original_idx in segment_modifications:
                    mod = segment_modifications[original_idx]
                    if mod.get("trim_start") is not None:
                        start += mod["trim_start"]
                        logger.info(f"Segment {original_idx}: trimming {mod['trim_start']}s from start (new start: {start:.1f}s)")
                    if mod.get("trim_end") is not None:
                        end -= mod["trim_end"]
                        logger.info(f"Segment {original_idx}: trimming {mod['trim_end']}s from end (new end: {end:.1f}s)")
                    
                    # Ensure valid range
                    if end <= start:
                        logger.warning(f"Segment {original_idx}: end <= start after trimming, using minimum 1s duration")
                        end = start + 1
                
                # Ensure we don't exceed video duration
                video_duration = source_video.duration
                start = max(0, min(start, video_duration))
                end = max(start + 0.1, min(end, video_duration))
                
                clip = source_video.subclipped(start, end)
                clips.append(clip)
                logger.info(f"Extracted segment {original_idx}: {start:.1f}s-{end:.1f}s (duration: {end-start:.1f}s)")
            
            if clips:
                # Concatenate clips (transitions handled by editor_agent in original reel)
                # For chatbot edits, use simple concatenation to avoid MoviePy 2.x API issues
                if len(clips) > 1:
                    logger.info(f"Concatenating {len(clips)} clips")
                    final_clip = concatenate_videoclips(clips, method="compose")
                else:
                    # Single clip
                    final_clip = clips[0]
                
                final_clip.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    fps=30,
                    logger=None  # Suppress verbose output
                )
                final_clip.close()
                for clip in clips:
                    clip.close()
            else:
                # No segments, return original
                source_video.write_videofile(
                    output_path,
                    codec='libx264',
                    audio_codec='aac',
                    fps=30
                )
            
            source_video.close()
        
        else:
            # Default: just copy the video
            source_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                fps=30
            )
            source_video.close()
        
        logger.info(f"Edited video saved to {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error applying editing instructions: {e}", exc_info=True)
        raise

