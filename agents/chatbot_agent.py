"""Chatbot Agent - Interactive video editing assistant."""
from typing import Dict, List, Optional
from pathlib import Path
import logging
import google.generativeai as genai
import os
from dotenv import load_dotenv
from .base_agent import BaseAgent

load_dotenv()
logger = logging.getLogger(__name__)


class ChatbotAgent(BaseAgent):
    """Interactive chatbot for video editing assistance."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("ChatbotAgent", config)
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = None
        if self.api_key:
            # Try models in order of preference (higher quota first)
            # Based on available models from API
            model_options = [
                'gemini-2.5-flash',  # Latest stable, good quota
                'gemini-2.0-flash-exp',  # Available, experimental
                'gemini-2.0-flash',  # Stable version
                'gemini-2.0-flash-001'  # Fallback
            ]
            for model_name in model_options:
                try:
                    self.model = genai.GenerativeModel(model_name)
                    self.log(f"Initialized chatbot with model: {model_name}", "info")
                    break
                except Exception as e:
                    self.log(f"Error initializing {model_name}: {e}, trying next...", "warning")
                    continue
            if not self.model:
                self.log("Failed to initialize any Gemini model", "error")
    
    def process(self, input_data: Dict) -> Dict:
        """
        Process input data (required by BaseAgent).
        
        This is a wrapper that can be used if needed, but typically
        process_edit_request() is called directly from the UI.
        """
        # If input_data contains an edit request, process it
        user_message = input_data.get("user_message", "")
        video_data = input_data.get("video_data", {})
        selected_clips = input_data.get("selected_clips", [])
        
        if user_message:
            return self.process_edit_request(user_message, video_data, selected_clips)
        else:
            return {
                "error": "No user message provided",
                "status": "error"
            }
    
    def create_context(self, video_data: Dict) -> str:
        """Create context string from video analysis data."""
        context_parts = []
        
        # Video metadata
        metadata = video_data.get("metadata", {})
        video_path = metadata.get("video_path", "Unknown")
        context_parts.append(f"Video: {Path(video_path).name}")
        
        # Events and plays
        events = video_data.get("events", [])
        plays = video_data.get("plays", [])
        
        if events:
            context_parts.append(f"\nDetected Events ({len(events)}):")
            for i, event in enumerate(events[:10]):  # Limit to first 10
                timestamp = event.get("timestamp", 0)
                desc = event.get("description", event.get("analysis", ""))[:100]
                successful = event.get("is_successful", False)
                score_change = event.get("is_score_change", False)
                context_parts.append(f"  {i+1}. {timestamp:.1f}s: {desc} (Success: {successful}, Score: {score_change})")
        
        if plays:
            context_parts.append(f"\nDetected Plays ({len(plays)}):")
            for i, play in enumerate(plays[:10]):
                timestamp = play.get("timestamp", 0)
                label = play.get("label", play.get("description", ""))
                context_parts.append(f"  {i+1}. {timestamp:.1f}s: {label}")
        
        # Segments
        segments = video_data.get("segments", [])
        if segments:
            context_parts.append(f"\nHighlight Segments ({len(segments)}):")
            for i, segment in enumerate(segments):
                start = segment.get("start_time", 0)
                end = segment.get("end_time", 0)
                desc = segment.get("description", "")[:80]
                context_parts.append(f"  {i+1}. {start:.1f}s-{end:.1f}s: {desc}")
        
        # Commentaries
        commentaries = video_data.get("commentaries", [])
        if commentaries:
            context_parts.append(f"\nCommentaries ({len(commentaries)}):")
            for i, comm in enumerate(commentaries):
                timestamp = comm.get("timestamp", 0)
                text = comm.get("text", "")[:80]
                context_parts.append(f"  {i+1}. {timestamp:.1f}s: {text}")
        
        return "\n".join(context_parts)
    
    def process_edit_request(self, user_message: str, video_data: Dict, selected_clips: List[str] = None) -> Dict:
        """Process user editing request and generate editing instructions."""
        if not self.model:
            return {
                "error": "Chatbot model not available. Please check API key configuration.",
                "editing_instructions": None
            }
        
        # Create context
        context = self.create_context(video_data)
        
        # Add selected clips context with segment mapping
        segments = video_data.get("segments", [])
        clips_context = ""
        if selected_clips:
            clips_context = f"\n\nSelected Clips for Editing:\n"
            for clip_path in selected_clips:
                clip_name = Path(clip_path).name
                # Try to find which segment this clip corresponds to
                # Clip names are like "segment_000.mp4", "segment_001.mp4", etc.
                try:
                    segment_idx = int(clip_name.replace("segment_", "").replace(".mp4", ""))
                    if segment_idx < len(segments):
                        segment = segments[segment_idx]
                        start = segment.get("start_time", 0)
                        end = segment.get("end_time", start + 10)
                        clips_context += f"  - {clip_name} (Segment {segment_idx + 1}, {start:.1f}s-{end:.1f}s)\n"
                    else:
                        clips_context += f"  - {clip_name}\n"
                except:
                    clips_context += f"  - {clip_name}\n"
        
        # Add segment count info for "last clip" references
        if segments:
            clips_context += f"\nTotal Segments: {len(segments)} (indices 0-{len(segments)-1})\n"
            clips_context += f"Last segment is index {len(segments)-1} (segment_{len(segments)-1:03d}.mp4)\n"
        
        # Create prompt
        prompt = f"""You are a video editing assistant for sports highlights. 

Video Analysis Context:
{context}
{clips_context}

User Request: {user_message}

Based on the video analysis and user request, provide specific editing instructions in JSON format:
{{
    "action": "edit_highlight_reel" or "edit_segment" or "add_effect" or "reorder" or "filter",
    "target": "highlight_reel" or "segment_X" or "all_segments",
    "instructions": "Detailed editing instructions",
    "parameters": {{
        "speed": "normal" or "slow_motion" or "fast_forward",
        "trim_start": null or seconds,
        "trim_end": null or seconds,
        "add_transitions": true/false,
        "focus_segments": [list of segment indices (0-based)],
        "remove_segments": [list of segment indices (0-based)],
        "modify_segments": [{{"index": segment_index, "trim_start": seconds_to_remove_from_start, "trim_end": seconds_to_remove_from_end}}]
    }}
}}

IMPORTANT RULES:
- If the user wants to REMOVE a clip/segment, use action: "edit_segment" and put the segment index (0-based) in remove_segments array
- If the user references a selected clip (like segment_000.mp4), that's segment index 0, segment_001.mp4 is index 1, etc.
- If the user says "remove this clip" and a clip is selected, use the segment index from the clip name
- Segment indices are 0-based (first segment is 0, second is 1, etc.)
- For removing segments, ALWAYS use action: "edit_segment" with remove_segments parameter
- If the user says "last clip" or "last segment", that means the LAST segment in the list (index = total_segments - 1)
- If the user wants to trim the end of a specific segment, use action: "edit_segment" with modify_segments parameter:
  - modify_segments: [{{"index": segment_index, "trim_end": seconds_to_remove_from_end}}]
  - Example: "remove 5 seconds from end of last clip" → modify_segments: [{{"index": last_segment_index, "trim_end": 5}}]

Be specific and actionable. If the user wants to edit specific clips, reference them by segment number or timestamp.
"""
        
        try:
            response = self.model.generate_content(prompt)
            instructions_text = response.text.strip()
            
            # Try to extract JSON from response
            import json
            import re
            
            # Look for JSON in the response
            json_match = re.search(r'\{.*\}', instructions_text, re.DOTALL)
            if json_match:
                instructions = json.loads(json_match.group())
            else:
                # Fallback: create basic instructions
                instructions = {
                    "action": "edit_highlight_reel",
                    "target": "highlight_reel",
                    "instructions": instructions_text,
                    "parameters": {}
                }
            
            return {
                "editing_instructions": instructions,
                "raw_response": instructions_text,
                "status": "success"
            }
            
        except Exception as e:
            error_msg = str(e)
            self.log(f"Error processing edit request: {error_msg}", "error")
            
            # Check for API key errors
            if "403" in error_msg or "leaked" in error_msg.lower() or "api key" in error_msg.lower():
                return {
                    "error": "API key issue detected. Your API key may have been reported as leaked. Please generate a new API key from Google AI Studio and update your .env file.",
                    "editing_instructions": None,
                    "status": "api_key_error",
                    "suggestion": "Get a new API key from https://aistudio.google.com/app/apikey and update GOOGLE_API_KEY in your .env file"
                }
            
            # Check for quota errors and try switching to a model with higher quota
            if "429" in error_msg or "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
                # Try to switch to a model with higher quota
                if self.model and hasattr(self.model, '_model_name'):
                    current_model = self.model._model_name if hasattr(self.model, '_model_name') else "unknown"
                    self.log(f"Quota error with {current_model}, trying to switch model...", "warning")
                
                # Try gemini-2.5-flash which should have higher quota
                try:
                    self.model = genai.GenerativeModel('gemini-2.5-flash')
                    self.log("Switched to gemini-2.5-flash for retry", "info")
                    # Retry the request once
                    try:
                        response = self.model.generate_content(prompt)
                        instructions_text = response.text.strip()
                        
                        import json
                        import re
                        json_match = re.search(r'\{.*\}', instructions_text, re.DOTALL)
                        if json_match:
                            instructions = json.loads(json_match.group())
                        else:
                            instructions = {
                                "action": "edit_highlight_reel",
                                "target": "highlight_reel",
                                "instructions": instructions_text,
                                "parameters": {}
                            }
                        
                        return {
                            "editing_instructions": instructions,
                            "raw_response": instructions_text,
                            "status": "success"
                        }
                    except Exception as retry_error:
                        self.log(f"Retry also failed: {retry_error}", "error")
                except Exception as switch_error:
                    self.log(f"Failed to switch model: {switch_error}", "error")
                
                return {
                    "error": "API quota exceeded. Please try again in a few minutes, or contact support to increase your quota.",
                    "editing_instructions": None,
                    "status": "quota_error",
                    "suggestion": "The system will automatically try a model with higher quotas on the next request."
                }
            
            return {
                "error": error_msg,
                "editing_instructions": None,
                "status": "error"
            }

