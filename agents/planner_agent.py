"""Planner Agent - decides highlight order and creates editing plan."""
from typing import Dict, List, Optional
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Plans highlight reel structure and ordering."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("PlannerAgent", config)
        from config import HIGHLIGHT_MIN_DURATION, HIGHLIGHT_MAX_DURATION, PRE_EVENT_BUFFER, POST_EVENT_BUFFER, SCORING_PLAY_PRE_BUFFER
        self.min_duration = config.get("min_duration", HIGHLIGHT_MIN_DURATION) if config else HIGHLIGHT_MIN_DURATION
        self.max_duration = config.get("max_duration", HIGHLIGHT_MAX_DURATION) if config else HIGHLIGHT_MAX_DURATION
        self.pre_buffer = config.get("pre_buffer", PRE_EVENT_BUFFER) if config else PRE_EVENT_BUFFER
        self.post_buffer = config.get("post_buffer", POST_EVENT_BUFFER) if config else POST_EVENT_BUFFER
        self.scoring_pre_buffer = config.get("scoring_pre_buffer", SCORING_PLAY_PRE_BUFFER) if config else SCORING_PLAY_PRE_BUFFER
    
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
        
        self.log(f"Input data: {len(events)} events, {len(plays)} plays, {len(key_frames)} key_frames", "info")
        
        # Combine all potential highlights
        all_moments = self._collect_moments(events, plays, key_frames, input_data)
        self.log(f"Collected {len(all_moments)} total moments", "info")
        
        # Score and rank moments
        ranked_moments = self._rank_moments(all_moments)
        self.log(f"Ranked {len(ranked_moments)} moments after filtering", "info")
        
        # If no ranked moments, use multiple fallbacks
        if not ranked_moments:
            self.log(f"No ranked moments found. Events: {len(events)}, Plays: {len(plays)}, Key frames: {len(key_frames)}", "warning")
            
            # Fallback 1: Use all events even if not ranked highly
            if events:
                self.log("Using all events as fallback", "info")
                for event in events[:15]:  # Top 15 events
                    ranked_moments.append({
                        "type": "event",
                        "start_time": event.get("timestamp", 0),
                        "end_time": event.get("timestamp", 0) + 5,
                        "timestamp": event.get("timestamp", 0),
                        "description": event.get("analysis", "Sports action"),
                        "source": "gemini_vision",
                        "confidence": event.get("confidence", 0.4),
                        "is_successful": event.get("is_successful", False),
                        "is_highlight": True,
                        "crowd_reaction": event.get("crowd_reaction", 5),
                        "importance_score": 0.4
                    })
            
            # Fallback 2: Use shot changes
            elif key_frames:
                self.log("Using shot changes as fallback", "warning")
                for i, frame in enumerate(key_frames[:10]):  # Top 10 shot changes
                    ranked_moments.append({
                        "type": "shot_change",
                        "start_time": frame.get("start_time", 0),
                        "end_time": frame.get("end_time", 0),
                        "timestamp": frame.get("start_time", 0),
                        "description": f"Action moment {i+1}",
                        "source": "video_intelligence",
                        "confidence": 0.5,
                        "is_successful": False,
                        "is_highlight": True,
                        "crowd_reaction": 5,
                        "importance_score": 0.5
                    })
            
            # Fallback 3: Use plays from Video Intelligence
            elif plays:
                self.log("Using Video Intelligence plays as fallback", "warning")
                for play in plays[:10]:
                    ranked_moments.append({
                        "type": "play",
                        "start_time": play.get("start_time", 0),
                        "end_time": play.get("end_time", 0),
                        "timestamp": play.get("start_time", 0),
                        "description": play.get("label", "Sports play"),
                        "source": "video_intelligence",
                        "confidence": play.get("confidence", 0.5),
                        "is_successful": False,
                        "is_highlight": True,
                        "crowd_reaction": 5,
                        "importance_score": 0.5
                    })
        
        # If still no ranked moments after all fallbacks, create segments from video timeline
        if not ranked_moments:
            self.log("No moments found even after fallbacks - creating timeline-based segments", "warning")
            # Get video duration from metadata if available
            metadata = input_data.get("metadata", {})
            video_path = metadata.get("video_path")
            if video_path:
                from utils.video_utils import get_video_info
                video_info = get_video_info(video_path)
                duration = video_info.get("duration", 0)
                if duration > 0:
                    # Create segments evenly spaced throughout video
                    num_segments = min(5, int(duration / 15))  # One segment every 15 seconds, max 5
                    segment_length = duration / num_segments if num_segments > 0 else 10
                    for i in range(num_segments):
                        start = i * segment_length
                        ranked_moments.append({
                            "type": "timeline",
                            "start_time": start,
                            "end_time": start + 10,
                            "timestamp": start,
                            "description": f"Video segment {i+1}",
                            "source": "timeline",
                            "confidence": 0.3,
                            "is_successful": False,
                            "is_highlight": True,
                            "crowd_reaction": 3,
                            "importance_score": 0.3
                        })
                    self.log(f"Created {len(ranked_moments)} timeline-based segments", "info")
        
        # Create segments with timing
        segments = self._create_segments(ranked_moments)
        self.log(f"Created {len(segments)} final segments", "info")
        
        # Always ensure the ending/last play is included
        metadata = input_data.get("metadata", {})
        video_path = metadata.get("video_path")
        if video_path:
            from utils.video_utils import get_video_info
            video_info = get_video_info(video_path)
            duration = video_info.get("duration", 0)
            
            if duration > 0:
                # Check if we already have a segment near the end (within last 20 seconds)
                has_ending = False
                for segment in segments:
                    segment_end = segment.get("end_time", 0)
                    if segment_end >= duration - 20:  # Within last 20 seconds
                        has_ending = True
                        break
                
                # If no ending segment, add one
                if not has_ending:
                    self.log("Adding ending segment to highlights", "info")
                    ending_start = max(0, duration - 15)  # Last 15 seconds
                    ending_end = duration
                    
                    # Check for overlap and adjust if needed
                    for segment in segments:
                        seg_start = segment.get("start_time", 0)
                        seg_end = segment.get("end_time", 0)
                        # If there's overlap, start the ending segment after the last segment
                        if seg_end > ending_start:
                            ending_start = seg_end + 1  # Start 1 second after last segment
                    
                    # Make sure we don't exceed video duration
                    ending_start = min(ending_start, duration - 10)
                    ending_end = duration
                    
                    if ending_end > ending_start:
                        segments.append({
                            "start_time": ending_start,
                            "end_time": ending_end,
                            "duration": ending_end - ending_start,
                            "event_start": ending_start,
                            "event_end": ending_end,
                            "type": "ending",
                            "description": "Final moments / Last play",
                            "importance": 0.9  # High importance for ending
                        })
                        self.log(f"Added ending segment: {ending_start}s - {ending_end}s", "info")
        
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
    
    def _collect_moments(self, events: List, plays: List, key_frames: List, input_data: Dict = None) -> List[Dict]:
        """Collect all potential highlight moments."""
        moments = []
        
        # Get video duration for ending detection
        duration = 0
        if input_data:
            metadata = input_data.get("metadata", {})
            video_path = metadata.get("video_path")
            if video_path:
                from utils.video_utils import get_video_info
                video_info = get_video_info(video_path)
                duration = video_info.get("duration", 0)
        
        # Add events from Gemini Vision - include ALL events
        for event in events:
            # Include all events, we'll rank them later
            timestamp = event.get("timestamp", 0)
            moment = {
                "type": "event",
                "timestamp": timestamp,
                "start_time": timestamp,
                "end_time": timestamp + 5,  # Default 5 second event
                "description": event.get("analysis", ""),
                "source": "gemini_vision",
                "confidence": event.get("confidence", 0.4),
                "is_successful": event.get("is_successful", False),
                "is_highlight": event.get("is_highlight", False),
                "is_score_change": event.get("is_score_change", False),  # Track score changes
                "is_close_game": event.get("is_close_game", False),  # Track close game situations
                "crowd_reaction": event.get("crowd_reaction", 3),  # Default to 3 if not set
                "has_action": event.get("has_action", True),  # Assume action if event exists
                "player_visible": event.get("player_visible", False),  # Track if player is visible
                "analysis": event.get("analysis", "")
            }
            
            # Boost importance of events near the end of video (last 30 seconds)
            if duration > 0 and timestamp >= duration - 30:
                moment["is_ending"] = True
                moment["confidence"] = moment.get("confidence", 0.4) + 0.3  # Boost confidence
                moment["is_highlight"] = True  # Mark as highlight
            
            moments.append(moment)
        
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
        """Rank moments by importance and excitement, prioritizing successful plays."""
        import random
        scored = []
        
        # Add small random variation to avoid always same clips
        # This makes each run slightly different while keeping best moments
        random_factor = 0.05  # 5% variation
        
        for moment in moments:
            score = moment.get("confidence", 0.5)
            
            # PRIORITY 1: Score changes are the MOST important - huge boost
            is_score_change = moment.get("is_score_change", False) or moment.get("is_successful", False)
            if is_score_change:
                score += 1.0  # MASSIVE boost for score changes (was 0.5)
                self.log(f"Score change detected at {moment.get('timestamp', 0)}s - major boost", "info")
            
            # PRIORITY 2: Close game situations get extra boost
            is_close_game = moment.get("is_close_game", False)
            if is_close_game:
                score += 0.6  # Big boost for close game situations
                self.log(f"Close game situation at {moment.get('timestamp', 0)}s - extra boost", "info")
            
            # PRIORITY 3: Score changes in close games = maximum priority
            if is_score_change and is_close_game:
                score += 0.5  # Additional boost for score changes in close games
                self.log(f"Score change in close game at {moment.get('timestamp', 0)}s - MAXIMUM priority", "info")
            
            # Prioritize ending moments (last 30 seconds) - especially if score change
            if moment.get("is_ending", False):
                if is_score_change:
                    score += 0.5  # Even bigger boost for ending score changes
                else:
                    score += 0.3  # Regular boost for ending moments
                self.log(f"Ending moment at {moment.get('timestamp', 0)}s", "info")
            
            # Filter out missed shots (but be less strict)
            analysis = moment.get("analysis", "").lower()
            # Only skip if explicitly marked as missed AND not successful AND not a score change
            if any(word in analysis for word in ["missed", "blocked", "failed"]):
                if not moment.get("is_successful", False) and not is_score_change and "missed" in analysis:
                    # Only skip if it's clearly a miss with low crowd reaction
                    if moment.get("crowd_reaction", 0) < 3:
                        continue  # Skip clearly missed shots with no excitement
                    else:
                        score -= 0.3  # Penalize but don't skip if there's excitement
            
            # Boost score for specific successful play types (score changes)
            label = moment.get("label", "").lower()
            description = moment.get("description", "").lower()
            
            if any(keyword in label or keyword in description 
                   for keyword in ["goal", "touchdown", "dunk", "home run", "score", "basket", "made", "scored"]):
                if "miss" not in label and "miss" not in description:
                    score += 0.4  # Increased boost for scoring keywords
            
            # REDUCED: Crowd reaction is less important than score changes
            # Only use crowd reaction if it's very high, and even then, less weight
            crowd_reaction = moment.get("crowd_reaction", 0)
            if crowd_reaction >= 8:  # Only very high reactions get boost
                score += 0.2  # Reduced from 0.3
            elif crowd_reaction >= 6:
                score += 0.1  # Reduced from 0.2
            # Lower crowd reactions don't get boost - score changes are more important
            
            # Be very lenient - include almost all moments
            if score < 0.2:
                continue  # Only skip extremely low scoring moments
            
            # Boost score for any action
            if moment.get("has_action", False):
                score += 0.2
            
            # Add small random variation to avoid always same clips
            score += random.uniform(-random_factor, random_factor)
            
            moment["importance_score"] = score
            scored.append(moment)
        
        # Sort by score (highest first)
        sorted_moments = sorted(scored, key=lambda x: x.get("importance_score", 0), reverse=True)
        
        # Occasionally shuffle top moments slightly for variation
        if len(sorted_moments) > 3 and random.random() < 0.3:  # 30% chance
            # Swap positions of 2nd and 3rd place occasionally
            sorted_moments[1], sorted_moments[2] = sorted_moments[2], sorted_moments[1]
        
        return sorted_moments
    
    def _create_segments(self, ranked_moments: List[Dict]) -> List[Dict]:
        """Create video segments from ranked moments, removing duplicates and overlaps."""
        segments = []
        
        # Take top moments (up to max_duration total)
        total_duration = 0
        max_total = 120  # 2 minutes max for highlight reel
        
        # Track used time ranges to avoid duplicates/overlaps
        used_ranges = []
        
        # If no ranked moments, create at least one segment from the beginning
        if not ranked_moments:
            self.log("No ranked moments - creating default segment from video start", "warning")
            segments.append({
                "start_time": 0,
                "end_time": 10,
                "duration": 10,
                "event_start": 0,
                "event_end": 10,
                "type": "default",
                "description": "Video highlight",
                "importance": 0.3
            })
            return segments
        
        for moment in ranked_moments:
            if total_duration >= max_total:
                break
            
            # Get the event timing
            event_start = moment.get("start_time", moment.get("timestamp", 0))
            event_end = moment.get("end_time", event_start + self.min_duration)
            
            # Check if this is a scoring play (basket, goal, score, etc.)
            description = moment.get("description", "").lower()
            analysis = moment.get("analysis", "").lower()
            is_scoring_play = (
                moment.get("is_successful", False) or
                any(word in description or word in analysis 
                    for word in ["basket", "goal", "score", "scored", "point", "touchdown", "made"])
            )
            
            # For scoring plays, we need to go back further to show the player shooting
            # The event_start might be when the ball goes in, but we need to show the setup
            if is_scoring_play:
                # Always use longer buffer for scoring plays to show the shooter
                # Ensure we capture the player preparing and shooting
                # Base is SCORING_PLAY_PRE_BUFFER (6s), add extra for player visibility
                if moment.get("player_visible", False):
                    pre_buffer = self.scoring_pre_buffer + 3  # 9 seconds total (6 + 3) to show shooter setup
                else:
                    pre_buffer = self.scoring_pre_buffer + 2  # 8 seconds (6 + 2) - player might be visible but not detected
                self.log(f"Extended pre-buffer for scoring play: {pre_buffer}s (to show shooter)", "info")
            else:
                pre_buffer = self.pre_buffer  # 2 seconds for regular events
            
            # IMPORTANT: For scoring plays, the event_start might be when ball goes in
            # We need to go back further to capture the shot attempt
            # If player_visible is False but it's a scoring play, still go back more
            if is_scoring_play:
                # Go back even further to ensure we capture the shot attempt
                segment_start = max(0, event_start - pre_buffer)
                # Also ensure we have enough time after to show the result
                segment_end = max(event_end + self.post_buffer, event_start + 8)  # At least 8s total
            else:
                # Regular events: standard buffers
                segment_start = max(0, event_start - pre_buffer)
                segment_end = event_end + self.post_buffer
            
            # Check for overlap with existing segments (within 3 seconds = duplicate)
            is_duplicate = False
            for used_start, used_end in used_ranges:
                # Check if segments overlap significantly (within 3 seconds)
                if (segment_start <= used_end + 3 and segment_end >= used_start - 3):
                    is_duplicate = True
                    break
            
            if is_duplicate:
                continue  # Skip duplicate segments
            
            # Calculate duration with buffers
            duration = segment_end - segment_start
            duration = max(duration, self.min_duration)  # Ensure minimum
            duration = min(duration, self.max_duration)  # Cap at maximum
            
            # Recalculate end time based on final duration
            final_end = segment_start + duration
            
            segments.append({
                "start_time": segment_start,
                "end_time": final_end,
                "duration": duration,
                "event_start": event_start,  # Original event time for reference
                "event_end": event_end,
                "type": moment.get("type"),
                "description": moment.get("label") or moment.get("description", ""),
                "importance": moment.get("importance_score", 0.5)
            })
            
            # Track this range
            used_ranges.append((segment_start, final_end))
            total_duration += duration
        
        return segments

