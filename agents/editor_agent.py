"""Editor Agent - uses Veo 3.1 to edit and enhance highlight clips."""
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class EditorAgent(BaseAgent):
    """Edits video segments using Veo 3.1 and creates highlight reel."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("EditorAgent", config)
        self.enable_veo = config.get("enable_veo", True) if config else True
        self.output_dir = Path(config.get("output_dir", "outputs")) if config else Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    def process(self, input_data: Dict) -> Dict:
        """
        Edit video segments and create highlight reel.
        
        Args:
            input_data: Dict with plan, segments, and video_path
            
        Returns:
            dict with edited_clips and final_highlight_reel path
        """
        self.log("Starting video editing", "info")
        
        # Try multiple paths to get segments
        plan = input_data.get("plan", {})
        segments = input_data.get("segments", []) or plan.get("segments", [])
        
        # Try multiple paths to get video_path
        metadata = input_data.get("metadata", {})
        video_path = (
            metadata.get("video_path") or
            input_data.get("video_path") or
            input_data.get("input", {}).get("video_path")
        )
        
        if not video_path:
            self.log(f"Available keys in input_data: {list(input_data.keys())}", "error")
            self.log(f"Metadata keys: {list(metadata.keys()) if metadata else 'None'}", "error")
            raise ValueError(f"Missing video_path. Available keys: {list(input_data.keys())}")
        
        if not segments:
            self.log("No segments found - no highlights detected", "warning")
            # Return empty result instead of error
            return {
                "highlight_reel": None,
                "clips": [],
                "segment_count": 0,
                "status": "no_segments"
            }
        
        # Extract segments from original video
        clips = self._extract_segments(video_path, segments)
        
        # Edit clips with Veo if enabled
        if self.enable_veo:
            edited_clips = self._edit_with_veo(clips, segments)
        else:
            edited_clips = clips
        
        # Compile final highlight reel
        highlight_reel = self._compile_reel(edited_clips, video_path)
        
        return {
            "highlight_reel": str(highlight_reel),
            "clips": [str(c) for c in edited_clips],
            "segment_count": len(segments),
            "status": "complete"
        }
    
    def _extract_segments(self, video_path: str, segments: List[Dict]) -> List[Path]:
        """Extract video segments using moviepy."""
        self.log(f"Extracting {len(segments)} segments", "info")
        
        try:
            from moviepy.editor import VideoFileClip
            clips = []
            
            source_video = VideoFileClip(video_path)
            
            for i, segment in enumerate(segments):
                start = segment.get("start_time", 0)
                end = segment.get("end_time", start + 10)
                
                # Ensure we don't exceed video duration
                video_duration = source_video.duration
                start = max(0, min(start, video_duration))
                end = min(end, video_duration)
                
                # Ensure end is after start
                if end <= start:
                    end = min(start + 5, video_duration)  # Default 5 second clip
                
                # Support both MoviePy 1.x (subclip) and 2.x (subclipped)
                if hasattr(source_video, 'subclipped'):
                    clip = source_video.subclipped(start, end)
                else:
                    clip = source_video.subclip(start, end)
                clip_path = self.output_dir / f"segment_{i:03d}.mp4"
                
                try:
                    clip.write_videofile(
                        str(clip_path),
                        codec='libx264',
                        audio_codec='aac',
                        temp_audiofile=str(self.output_dir / f"temp_audio_{i}.m4a"),
                        remove_temp=True,
                        logger=None  # Suppress verbose output
                    )
                    clips.append(clip_path)
                    self.log(f"Extracted segment {i}: {start}s - {end}s", "info")
                except BrokenPipeError as e:
                    self.log(f"Broken pipe error extracting segment {i}: {e}", "error")
                    raise
                except Exception as e:
                    self.log(f"Error extracting segment {i}: {e}", "error")
                    raise
                finally:
                    # Always close the clip after writing (even on error)
                    try:
                        clip.close()
                    except Exception:
                        pass  # Ignore errors during cleanup
            
            source_video.close()
            return clips
            
        except Exception as e:
            self.log(f"Error extracting segments: {e}", "error")
            raise
    
    def _edit_with_veo(self, clips: List[Path], segments: List[Dict]) -> List[Path]:
        """Edit clips using Veo 3.1."""
        self.log("Editing clips with Veo 3.1", "info")
        
        if not self.enable_veo:
            return clips
        
        edited_clips = []
        
        try:
            import google.generativeai as genai
            from config import GOOGLE_API_KEY
            
            if not GOOGLE_API_KEY:
                self.log("Google API key not configured, skipping Veo editing", "warning")
                return clips
            
            genai.configure(api_key=GOOGLE_API_KEY)
            
            # Note: Veo 3.1 API integration would go here
            # This is a placeholder for the actual Veo API call
            for i, (clip_path, segment) in enumerate(zip(clips, segments)):
                self.log(f"Processing clip {i} with Veo", "info")
                
                description = segment.get("description", "")
                prompt = f"""
                Enhance this sports highlight clip:
                - Add slow-motion effect to key moments
                - Stabilize camera shake
                - Enhance lighting and contrast
                - Add smooth transitions
                - Maintain the original action and timing
                
                Clip description: {description}
                """
                
                # Placeholder: Actual Veo API call would be:
                # veo_model = genai.GenerativeModel('veo-3.1')
                # edited = veo_model.edit_video(
                #     input_video=clip_path,
                #     instructions=prompt
                # )
                
                # For now, return original clips
                edited_clips.append(clip_path)
            
            return edited_clips
            
        except Exception as e:
            self.log(f"Veo editing error: {e}, using original clips", "warning")
            return clips
    
    def _compile_reel(self, clips: List[Path], source_video: str) -> Path:
        """Compile all clips into final highlight reel with crossfade transitions."""
        self.log("Compiling highlight reel with crossfade transitions", "info")
        
        try:
            from moviepy.editor import VideoFileClip, CompositeVideoClip, concatenate_videoclips
            from config import TRANSITION_DURATION
            
            video_clips = [VideoFileClip(str(clip)) for clip in clips]
            
            if not video_clips:
                raise ValueError("No clips to compile")
            
            transition_duration = TRANSITION_DURATION
            
            # Create smooth crossfade transitions using concatenate with negative padding
            if len(video_clips) == 1:
                final_reel = video_clips[0]
            else:
                import numpy as np
                
                self.log(f"Creating crossfade reel: {len(video_clips)} clips with {transition_duration}s transitions", "info")
                
                # Apply fade effects to clips for crossfade
                faded_clips = []
                for i, clip in enumerate(video_clips):
                    clip_duration = clip.duration
                    
                    if i == 0:
                        # First clip: fade out at end
                        if clip_duration > transition_duration:
                            def fadeout(get_frame, t):
                                frame = get_frame(t)
                                if t >= clip_duration - transition_duration:
                                    fade_progress = (t - (clip_duration - transition_duration)) / transition_duration
                                    opacity = 1.0 - fade_progress
                                    return (frame * opacity).astype(np.uint8)
                                return frame
                            clip = clip.fl(fadeout)
                        faded_clips.append(clip)
                    
                    elif i == len(video_clips) - 1:
                        # Last clip: fade in at start
                        if clip_duration > transition_duration:
                            def fadein(get_frame, t):
                                frame = get_frame(t)
                                if t <= transition_duration:
                                    opacity = t / transition_duration
                                    return (frame * opacity).astype(np.uint8)
                                return frame
                            clip = clip.fl(fadein)
                        faded_clips.append(clip)
                    
                    else:
                        # Middle clips: fade in at start AND fade out at end
                        if clip_duration > transition_duration * 2:
                            def fadeboth(get_frame, t):
                                frame = get_frame(t)
                                if t <= transition_duration:
                                    opacity = t / transition_duration
                                    return (frame * opacity).astype(np.uint8)
                                elif t >= clip_duration - transition_duration:
                                    fade_progress = (t - (clip_duration - transition_duration)) / transition_duration
                                    opacity = 1.0 - fade_progress
                                    return (frame * opacity).astype(np.uint8)
                                return frame
                            clip = clip.fl(fadeboth)
                        faded_clips.append(clip)
                
                # Concatenate with negative padding to create overlap for crossfade
                # Negative padding makes clips overlap by transition_duration
                final_reel = concatenate_videoclips(faded_clips, method="compose", padding=-transition_duration)
                self.log(f"Final reel created with {transition_duration}s crossfade transitions", "info")
            output_path = self.output_dir / "highlight_reel.mp4"
            
            try:
                final_reel.write_videofile(
                    str(output_path),
                    codec='libx264',
                    audio_codec='aac',
                    fps=30,
                    logger=None  # Suppress verbose output
                )
            except BrokenPipeError as e:
                self.log(f"Broken pipe error during video write: {e}", "error")
                # Try to cleanup before re-raising
                try:
                    for clip in video_clips:
                        clip.close()
                    final_reel.close()
                except:
                    pass
                raise
            except Exception as e:
                self.log(f"Error writing video file: {e}", "error")
                # Cleanup on any error
                try:
                    for clip in video_clips:
                        clip.close()
                    final_reel.close()
                except:
                    pass
                raise
            
            # Cleanup
            try:
                for clip in video_clips:
                    clip.close()
                final_reel.close()
            except Exception as cleanup_error:
                self.log(f"Error during cleanup: {cleanup_error}", "warning")
            
            self.log(f"Highlight reel with transitions saved to {output_path}", "info")
            return output_path
            
        except Exception as e:
            self.log(f"Error compiling reel with transitions: {e}", "error")
            # Fallback: simple concatenation
            try:
                from moviepy.editor import VideoFileClip, concatenate_videoclips
                video_clips = [VideoFileClip(str(clip)) for clip in clips]
                final_reel = concatenate_videoclips(video_clips, method="compose")
                output_path = self.output_dir / "highlight_reel.mp4"
                try:
                    final_reel.write_videofile(
                        str(output_path), 
                        codec='libx264', 
                        audio_codec='aac', 
                        fps=30,
                        logger=None  # Suppress verbose output
                    )
                except BrokenPipeError as e:
                    self.log(f"Broken pipe error in fallback: {e}", "error")
                    try:
                        for clip in video_clips:
                            clip.close()
                        final_reel.close()
                    except:
                        pass
                    raise
                finally:
                    try:
                        for clip in video_clips:
                            clip.close()
                        final_reel.close()
                    except Exception as cleanup_error:
                        self.log(f"Error during fallback cleanup: {cleanup_error}", "warning")
                self.log("Created reel without transitions (fallback)", "warning")
                return output_path
            except Exception as e2:
                self.log(f"Fallback also failed: {e2}", "error")
                raise

