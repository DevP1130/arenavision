"""Vision Agent - analyzes video using Google Video Intelligence and Gemini Vision."""
# Apply Python 3.9 compatibility fix before importing Google Cloud libraries
import sys
if sys.version_info < (3, 10):
    try:
        import compat_fix  # Apply compatibility shim
    except ImportError:
        pass  # If compat_fix not found, continue anyway

from typing import Dict, List, Optional, Union
from pathlib import Path
import logging
import re
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
            from google.oauth2 import service_account
            from utils.video_utils import get_video_info
            from config import GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT
            import os
            
            # Check video duration - use faster features for short videos
            video_info = get_video_info(video_path)
            duration = video_info.get("duration", 0)
            is_short_video = duration < 180  # Less than 3 minutes
            
            # Set up credentials explicitly
            credentials = None
            if GOOGLE_APPLICATION_CREDENTIALS:
                creds_path = GOOGLE_APPLICATION_CREDENTIALS
                # Handle relative paths
                if not os.path.isabs(creds_path):
                    creds_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), creds_path)
                
                if os.path.exists(creds_path):
                    credentials = service_account.Credentials.from_service_account_file(creds_path)
                    self.log(f"Using credentials from: {creds_path}", "info")
                else:
                    self.log(f"Credentials file not found: {creds_path}", "warning")
            
            # Create client with explicit credentials if available
            if credentials:
                client = vi.VideoIntelligenceServiceClient(credentials=credentials)
            else:
                # Try default credentials (from environment)
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
            
            # Adjust number of frames based on video length - sample throughout entire video
            video_info = get_video_info(video_path)
            duration = video_info.get("duration", 0)
            
            # Sample more frames for longer videos to cover entire video
            if duration < 120:  # Less than 2 minutes
                num_frames = 10
            elif duration < 300:  # Less than 5 minutes
                num_frames = 20
            elif duration < 600:  # Less than 10 minutes
                num_frames = 30
            else:
                num_frames = 40  # For very long videos
            
            frames_data = sample_key_frames(video_path, num_frames=num_frames)
            
            events = []
            for frame_image, timestamp, frame_idx in frames_data:
                prompt = """
                Analyze this sports frame and identify:
                1. What sport is being played?
                2. Is there a shot attempt (basketball), goal attempt (soccer), or scoring play?
                3. Was the shot/goal SUCCESSFUL (made basket, goal scored) or MISSED (ball missed, shot blocked)?
                4. Can you see a player preparing to shoot/score (player with ball, shooting motion, etc.)?
                5. Player positions and movements
                6. Is this a SCORE CHANGE moment? (Did the score change on this play?)
                7. Does the game appear CLOSE? (Look for scoreboard, tight game situation, late game, etc.)
                8. Crowd reaction level (0-10) - but this is less important than score changes
                
                IMPORTANT: 
                - Focus heavily on SCORE CHANGES - these are the most important moments
                - Close game situations (tight score, late in game) are especially important
                - Only mark as highlight if the shot/goal was SUCCESSFUL
                - If you see a successful score, also note if you can see the player shooting/scoring
                - Missed shots should NOT be highlights
                - Score changes are more important than crowd reaction
                
                Respond in this exact JSON format:
                {
                    "sport": "basketball/soccer/etc",
                    "action": "shot/goal/tackle/etc",
                    "successful": true/false,
                    "player_visible": true/false,
                    "score_change": true/false,
                    "close_game": true/false,
                    "crowd_reaction": 0-10,
                    "is_highlight": true/false
                }
                """
                
                response = model.generate_content([prompt, frame_image])
                response_text = response.text.strip()
                
                # Parse response to check for successful plays
                is_successful = False
                is_highlight = False
                crowd_reaction = 0
                is_score_change = False
                is_close_game = False
                
                # Check for successful indicators (score changes)
                if any(word in response_text.lower() for word in ["successful", "made", "scored", "goal", "basket", "point"]):
                    if not any(word in response_text.lower() for word in ["missed", "blocked", "failed", "unsuccessful"]):
                        is_successful = True
                        # If successful, it's likely a score change
                        is_score_change = True
                
                # Explicitly check for score change mentions
                if any(phrase in response_text.lower() for phrase in [
                    "score change", "score changed", "point scored", "goal scored", 
                    "basket made", "score", "scored", "point"
                ]):
                    if "miss" not in response_text.lower() and "block" not in response_text.lower():
                        is_score_change = True
                
                # Check for close game situations
                if any(phrase in response_text.lower() for phrase in [
                    "close", "tight", "tied", "close game", "late game", "final", 
                    "overtime", "crunch time", "clutch", "game on the line"
                ]):
                    is_close_game = True
                
                # Check if player is visible (for extending segment to show shooter)
                player_visible = any(word in response_text.lower() for word in [
                    "player", "shooting", "shooter", "with ball", "preparing", "taking shot"
                ])
                
                # Check for highlight indicators
                if "highlight" in response_text.lower() or "highlight-worthy" in response_text.lower():
                    is_highlight = True
                
                # Extract crowd reaction if mentioned (but it's less important now)
                crowd_match = re.search(r'crowd[_\s]*reaction[:\s]*(\d+)', response_text.lower())
                if crowd_match:
                    crowd_reaction = int(crowd_match.group(1))
                elif "crowd" in response_text.lower() and any(word in response_text.lower() for word in ["cheer", "excit", "loud"]):
                    crowd_reaction = 7
                
                # Be very lenient - include ANY frame that might have action
                # Check if there's any sports action at all
                has_action = any(word in response_text.lower() for word in [
                    "sport", "basketball", "soccer", "football", "player", "ball", 
                    "shot", "goal", "score", "play", "game", "court", "field"
                ])
                
                # Include if it's a highlight, successful (score change), has crowd reaction, OR has any sports action
                # Prioritize score changes heavily
                if is_highlight or is_successful or is_score_change or crowd_reaction >= 3 or has_action:
                    events.append({
                        "frame_index": frame_idx,
                        "timestamp": timestamp,  # Actual timestamp from video
                        "analysis": response_text,
                        "is_highlight": is_highlight or is_successful or is_score_change,
                        "is_successful": is_successful,
                        "is_score_change": is_score_change,  # Track score changes
                        "is_close_game": is_close_game,  # Track close game situations
                        "player_visible": player_visible,
                        "crowd_reaction": crowd_reaction,
                        "has_action": has_action,
                        # Boost confidence for score changes and close games
                        "confidence": max(
                            (0.7 if is_score_change else 0.4) + (0.2 if is_close_game else 0),
                            crowd_reaction / 10.0,
                            0.4 if has_action else 0.3
                        )
                    })
            
            self.log(f"Gemini Vision detected {len(events)} events", "info")
            
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

