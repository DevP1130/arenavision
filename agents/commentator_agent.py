"""Commentator Agent - generates commentary using Gemini and TTS."""
from typing import Dict, List, Optional
from pathlib import Path
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CommentatorAgent(BaseAgent):
    """Generates text and audio commentary for highlights."""
    
    def __init__(self, config: Optional[dict] = None):
        super().__init__("CommentatorAgent", config)
        self.enable_tts = config.get("enable_tts", True) if config else True
        self.output_dir = Path(config.get("output_dir", "outputs")) if config else Path("outputs")
        self.output_dir.mkdir(exist_ok=True)
    
    def process(self, input_data: Dict) -> Dict:
        """
        Generate commentary for highlight reel.
        
        Args:
            input_data: Dict with segments, highlight_reel, and metadata
            
        Returns:
            dict with commentary_text, audio_file, and timestamps
        """
        self.log("Generating commentary", "info")
        
        segments = input_data.get("segments", [])
        plan = input_data.get("plan", {})
        
        if not segments:
            return {"commentary": [], "status": "no_segments"}
        
        # Generate commentary for each segment
        commentaries = []
        
        for i, segment in enumerate(segments):
            commentary = self._generate_segment_commentary(segment, i, len(segments))
            commentaries.append(commentary)
        
        # Generate overall narration
        overall_narration = self._generate_overall_narration(plan, segments)
        
        # Generate audio if TTS enabled
        audio_file = None
        if self.enable_tts:
            audio_file = self._generate_audio(commentaries, overall_narration)
        
        return {
            "commentaries": commentaries,
            "overall_narration": overall_narration,
            "audio_file": str(audio_file) if audio_file else None,
            "status": "complete"
        }
    
    def _generate_segment_commentary(self, segment: Dict, index: int, total: int) -> Dict:
        """Generate commentary for a single segment."""
        try:
            import google.generativeai as genai
            from config import GOOGLE_API_KEY
            
            if not GOOGLE_API_KEY:
                return {
                    "segment_index": index,
                    "text": f"Highlight {index + 1} of {total}",
                    "timestamp": segment.get("start_time", 0)
                }
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            description = segment.get("description", "")
            importance = segment.get("importance", 0.5)
            
            prompt = f"""
            Write exciting sports commentary for this highlight moment:
            
            Description: {description}
            Importance: {importance:.2f}
            Position in reel: {index + 1} of {total}
            
            Write 1-2 sentences of energetic, professional sports commentary.
            Keep it concise and exciting. Match the energy level to the importance score.
            """
            
            response = model.generate_content(prompt)
            commentary_text = response.text.strip()
            
            return {
                "segment_index": index,
                "text": commentary_text,
                "timestamp": segment.get("start_time", 0),
                "duration": segment.get("duration", 10)
            }
            
        except Exception as e:
            self.log(f"Error generating commentary: {e}", "error")
            return {
                "segment_index": index,
                "text": f"Exciting moment {index + 1}!",
                "timestamp": segment.get("start_time", 0)
            }
    
    def _generate_overall_narration(self, plan: Dict, segments: List[Dict]) -> str:
        """Generate overall narration for the highlight reel."""
        try:
            import google.generativeai as genai
            from config import GOOGLE_API_KEY
            
            if not GOOGLE_API_KEY:
                return "Here are the top highlights from the game."
            
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            highlight_count = len(segments)
            total_duration = plan.get("total_duration", 60)
            
            prompt = f"""
            Write a brief introduction (1-2 sentences) for a sports highlight reel.
            
            The reel contains {highlight_count} highlights totaling {total_duration} seconds.
            Make it exciting and set the stage for the highlights.
            """
            
            response = model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            self.log(f"Error generating narration: {e}", "error")
            return "Welcome to the game highlights!"
    
    def _generate_audio(self, commentaries: List[Dict], narration: str) -> Optional[Path]:
        """Generate audio file using TTS."""
        if not self.enable_tts:
            return None
        
        try:
            from gtts import gTTS
            import io
            from pydub import AudioSegment
            from pydub.playback import play
            
            audio_segments = []
            
            # Generate narration audio
            tts = gTTS(text=narration, lang='en', slow=False)
            narration_audio = io.BytesIO()
            tts.write_to_fp(narration_audio)
            narration_audio.seek(0)
            audio_segments.append(AudioSegment.from_mp3(narration_audio))
            
            # Generate commentary audio for each segment
            for commentary in commentaries:
                text = commentary.get("text", "")
                if text:
                    tts = gTTS(text=text, lang='en', slow=False)
                    commentary_audio = io.BytesIO()
                    tts.write_to_fp(commentary_audio)
                    commentary_audio.seek(0)
                    audio_segments.append(AudioSegment.from_mp3(commentary_audio))
            
            # Combine all audio
            if audio_segments:
                final_audio = sum(audio_segments)
                output_path = self.output_dir / "commentary.mp3"
                final_audio.export(str(output_path), format="mp3")
                
                self.log(f"Commentary audio saved to {output_path}", "info")
                return output_path
            
            return None
            
        except Exception as e:
            self.log(f"TTS error: {e}", "warning")
            return None

