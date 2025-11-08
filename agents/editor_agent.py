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
        
        plan = input_data.get("plan", {})
        segments = plan.get("segments", [])
        video_path = input_data.get("metadata", {}).get("video_path")
        
        if not video_path or not segments:
            raise ValueError("Missing video_path or segments")
        
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
            from moviepy import VideoFileClip
            clips = []
            
            source_video = VideoFileClip(video_path)
            
            for i, segment in enumerate(segments):
                start = segment.get("start_time", 0)
                end = segment.get("end_time", start + 10)
                
                # MoviePy 2.x uses subclipped instead of subclip
                clip = source_video.subclipped(start, min(end, source_video.duration))
                clip_path = self.output_dir / f"segment_{i:03d}.mp4"
                
                clip.write_videofile(
                    str(clip_path),
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile=str(self.output_dir / f"temp_audio_{i}.m4a"),
                    remove_temp=True
                )
                
                clips.append(clip_path)
                self.log(f"Extracted segment {i}: {start}s - {end}s", "info")
            
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
        """Compile all clips into final highlight reel."""
        self.log("Compiling highlight reel", "info")
        
        try:
            from moviepy import VideoFileClip, concatenate_videoclips
            
            video_clips = [VideoFileClip(str(clip)) for clip in clips]
            
            if not video_clips:
                raise ValueError("No clips to compile")
            
            final_reel = concatenate_videoclips(video_clips, method="compose")
            output_path = self.output_dir / "highlight_reel.mp4"
            
            final_reel.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                fps=30
            )
            
            # Cleanup
            for clip in video_clips:
                clip.close()
            final_reel.close()
            
            self.log(f"Highlight reel saved to {output_path}", "info")
            return output_path
            
        except Exception as e:
            self.log(f"Error compiling reel: {e}", "error")
            raise

