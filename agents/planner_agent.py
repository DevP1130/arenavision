"""Planner Agent - decides highlight order and creates editing plan."""
from typing import Dict, List, Optional
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Plans highlight reel structure and ordering."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("PlannerAgent", config)
        self.min_duration = config.get("min_duration", 3) if config else 3
        self.max_duration = config.get("max_duration", 30) if config else 30
    
    def process(self, input_data: Dict) -> Dict:
        """
        Create a plan for highlight reel from vision analysis.
        
        Args:
            input_data: Dict with detections, events, plays from VisionAgent
            
        Returns:
            dict with highlight_plan, segments, and ordering
        """
        self.log("Creating highlight plan", "info")
        
        detections = input_data.get("detections", {})
        events = input_data.get("events", [])
        plays = input_data.get("plays", [])
        key_frames = input_data.get("key_frames", [])
        
        # Combine all potential highlights
        all_moments = self._collect_moments(events, plays, key_frames)
        
        # Score and rank moments
        ranked_moments = self._rank_moments(all_moments)
        
        # Create segments with timing
        segments = self._create_segments(ranked_moments)
        
        # Generate editing plan
        plan = {
            "segments": segments,
            "total_duration": sum(s.get("duration", 10) for s in segments),
            "highlight_count": len(segments),
            "ordering": "chronological"  # or "importance", "dramatic"
        }
        
        self.log(f"Created plan with {len(segments)} highlights", "info")
        
        return {
            "plan": plan,
            "segments": segments,
            "metadata": {
                "total_moments_found": len(all_moments),
                "highlights_selected": len(segments)
            }
        }
    
    def _collect_moments(self, events: List, plays: List, key_frames: List) -> List[Dict]:
        """Collect all potential highlight moments."""
        moments = []
        
        # Add events from Gemini Vision
        for event in events:
            if event.get("is_highlight"):
                moments.append({
                    "type": "event",
                    "timestamp": event.get("timestamp", 0),
                    "description": event.get("analysis", ""),
                    "source": "gemini_vision",
                    "confidence": 0.8
                })
        
        # Add plays from Video Intelligence
        for play in plays:
            moments.append({
                "type": "play",
                "start_time": play.get("start_time", 0),
                "end_time": play.get("end_time", 0),
                "label": play.get("label", ""),
                "source": "video_intelligence",
                "confidence": play.get("confidence", 0.7)
            })
        
        # Add key frames (shot changes might indicate action)
        for frame in key_frames:
            moments.append({
                "type": "shot_change",
                "start_time": frame.get("start_time", 0),
                "end_time": frame.get("end_time", 0),
                "source": "video_intelligence",
                "confidence": 0.6
            })
        
        return moments
    
    def _rank_moments(self, moments: List[Dict]) -> List[Dict]:
        """Rank moments by importance and excitement."""
        scored = []
        
        for moment in moments:
            score = moment.get("confidence", 0.5)
            
            # Boost score for specific play types
            label = moment.get("label", "").lower()
            description = moment.get("description", "").lower()
            
            if any(keyword in label or keyword in description 
                   for keyword in ["goal", "touchdown", "dunk", "home run", "score"]):
                score += 0.3
            
            if "crowd" in description and "10" in description:
                score += 0.2
            
            moment["importance_score"] = score
            scored.append(moment)
        
        # Sort by score (highest first)
        return sorted(scored, key=lambda x: x.get("importance_score", 0), reverse=True)
    
    def _create_segments(self, ranked_moments: List[Dict]) -> List[Dict]:
        """Create video segments from ranked moments."""
        segments = []
        
        # Take top moments (up to max_duration total)
        total_duration = 0
        max_total = 120  # 2 minutes max for highlight reel
        
        for moment in ranked_moments:
            if total_duration >= max_total:
                break
            
            start = moment.get("start_time", moment.get("timestamp", 0))
            end = moment.get("end_time", start + self.min_duration)
            
            # Ensure minimum duration
            duration = max(end - start, self.min_duration)
            duration = min(duration, self.max_duration)
            
            segments.append({
                "start_time": start,
                "end_time": start + duration,
                "duration": duration,
                "type": moment.get("type"),
                "description": moment.get("label") or moment.get("description", ""),
                "importance": moment.get("importance_score", 0.5)
            })
            
            total_duration += duration
        
        return segments

