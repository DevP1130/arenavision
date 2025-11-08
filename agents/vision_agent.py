"""Vision Agent - analyzes video using Google Video Intelligence and Gemini Vision."""
from typing import Dict, List, Optional, Union
from pathlib import Path
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class VisionAgent(BaseAgent):
    """Analyzes video content for plays, events, and key moments."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("VisionAgent", config)
        self.use_video_intelligence = config.get("use_video_intelligence", True) if config else True
        self.use_gemini_vision = config.get("use_gemini_vision", True) if config else True
    
    def process(self, input_data: Union[str, Path, Dict]) -> Dict:
        """
        Analyze video for key events and plays.
        
        Args:
            input_data: Video path or dict with video_path and mode
            
        Returns:
            dict with detections, key_frames, and events
        """
        if isinstance(input_data, dict):
            video_path = input_data.get("video_path")
            mode = input_data.get("mode", "youtube")
        else:
            video_path = str(input_data)
            mode = "youtube"
        
        self.log(f"Analyzing video: {video_path} (mode: {mode})", "info")
        
        detections = {}
        
        # Use Google Video Intelligence API
        if self.use_video_intelligence and video_path:
            detections.update(self._analyze_with_video_intelligence(video_path))
        
        # Use Gemini Vision for key frame analysis
        if self.use_gemini_vision:
            detections.update(self._analyze_with_gemini_vision(video_path, mode))
        
        return {
            "detections": detections,
            "key_frames": detections.get("key_frames", []),
            "events": detections.get("events", []),
            "plays": detections.get("plays", []),
            "metadata": {
                "video_path": video_path,
                "mode": mode,
                "analysis_complete": True
            }
        }
    
    def _analyze_with_video_intelligence(self, video_path: str) -> Dict:
        """Analyze video using Google Video Intelligence API."""
        self.log("Running Video Intelligence API analysis", "info")
        
        try:
            from google.cloud import videointelligence_v1 as vi
            from utils.video_utils import get_video_info
            
            # Check video duration - use faster features for short videos
            video_info = get_video_info(video_path)
            duration = video_info.get("duration", 0)
            is_short_video = duration < 180  # Less than 3 minutes
            
            client = vi.VideoIntelligenceServiceClient()
            
            # For short videos, use fewer features for faster processing
            if is_short_video:
                self.log(f"Short video ({duration:.1f}s) - using fast mode", "info")
                features = [
                    vi.Feature.SHOT_CHANGE_DETECTION,  # Fast and useful
                    vi.Feature.LABEL_DETECTION,  # Essential for sports
                ]
            else:
                # Full features for longer videos
                features = [
                    vi.Feature.LABEL_DETECTION,
                    vi.Feature.SHOT_CHANGE_DETECTION,
                    vi.Feature.OBJECT_TRACKING,
                ]
                # Skip slow features for faster processing
                # vi.Feature.EXPLICIT_CONTENT_DETECTION,  # Slow, not needed for sports
                # vi.Feature.TEXT_DETECTION,  # Slow, can use Gemini Vision instead
            
            with open(video_path, "rb") as video_file:
                input_content = video_file.read()
            
            operation = client.annotate_video(
                request={
                    "features": features,
                    "input_content": input_content,
                }
            )
            
            self.log("Waiting for Video Intelligence analysis...", "info")
            result = operation.result(timeout=300)  # 5 minute timeout
            
            # Parse results
            annotations = result.annotation_results[0]
            
            events = []
            key_frames = []
            plays = []
            
            # Extract shot changes (potential highlight moments)
            for shot in annotations.shot_annotations:
                key_frames.append({
                    "start_time": shot.start_time_offset.total_seconds(),
                    "end_time": shot.end_time_offset.total_seconds(),
                    "type": "shot_change"
                })
            
            # Extract labels (sports-related events)
            for label in annotations.segment_label_annotations:
                if any(keyword in label.entity.description.lower() 
                       for keyword in ["goal", "score", "touchdown", "basket", "dunk", "tackle", "catch"]):
                    for segment in label.segments:
                        plays.append({
                            "start_time": segment.segment.start_time_offset.total_seconds(),
                            "end_time": segment.segment.end_time_offset.total_seconds(),
                            "label": label.entity.description,
                            "confidence": segment.confidence
                        })
            
            return {
                "video_intelligence": {
                    "shots": key_frames,
                    "plays": plays,
                    "labels": [label.entity.description for label in annotations.segment_label_annotations]
                },
                "key_frames": key_frames,
                "plays": plays
            }
            
        except Exception as e:
            self.log(f"Video Intelligence API error: {e}", "error")
            # Return empty structure if API fails
            return {
                "video_intelligence": {},
                "key_frames": [],
                "plays": []
            }
    
    def _analyze_with_gemini_vision(self, video_path: Optional[str], mode: str) -> Dict:
        """Analyze key frames using Gemini Vision."""
        self.log("Running Gemini Vision analysis", "info")
        
        try:
            import google.generativeai as genai
            from config import GOOGLE_API_KEY
            
            if not GOOGLE_API_KEY:
                self.log("Google API key not configured", "warning")
                return {}
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            # For live mode or large videos, sample key frames
            if mode == "live" or not video_path:
                # Return structure for live processing
                return {
                    "gemini_vision": {
                        "mode": "live",
                        "ready_for_frame_analysis": True
                    }
                }
            
            # For uploaded/YouTube videos, analyze sampled frames
            from utils.video_utils import sample_key_frames, get_video_info
            
            # Adjust number of frames based on video length
            video_info = get_video_info(video_path)
            duration = video_info.get("duration", 0)
            
            # Use fewer frames for shorter videos (faster processing)
            if duration < 120:  # Less than 2 minutes
                num_frames = 5
            elif duration < 300:  # Less than 5 minutes
                num_frames = 8
            else:
                num_frames = 10
            
            frames = sample_key_frames(video_path, num_frames=num_frames)
            
            events = []
            for i, frame in enumerate(frames):
                prompt = """
                Analyze this sports frame and identify:
                1. What sport is being played?
                2. Any significant action (goal, score, tackle, catch, etc.)?
                3. Player positions and movements
                4. Crowd reaction level (0-10)
                5. Is this a highlight-worthy moment? (yes/no)
                
                Respond in JSON format.
                """
                
                response = model.generate_content([prompt, frame])
                
                # Parse response (simplified)
                events.append({
                    "frame_index": i,
                    "timestamp": i * 3,  # Approximate timestamp
                    "analysis": response.text,
                    "is_highlight": "highlight" in response.text.lower()
                })
            
            return {
                "gemini_vision": {
                    "events": events,
                    "highlights_detected": [e for e in events if e.get("is_highlight")]
                },
                "events": events
            }
            
        except Exception as e:
            self.log(f"Gemini Vision error: {e}", "error")
            return {}

