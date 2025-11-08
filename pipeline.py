"""Main pipeline orchestrator for Game Watcher AI."""
from typing import Dict, Optional
import logging
from pathlib import Path

from agents import (
    InputAgent,
    VisionAgent,
    PlannerAgent,
    EditorAgent,
    CommentatorAgent
)
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GameWatcherPipeline:
    """Main pipeline that orchestrates all agents."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        
        # Initialize agents
        self.input_agent = InputAgent(self.config.get("input", {}))
        self.vision_agent = VisionAgent(self.config.get("vision", {}))
        self.planner_agent = PlannerAgent(self.config.get("planner", {}))
        self.editor_agent = EditorAgent(self.config.get("editor", {}))
        self.commentator_agent = CommentatorAgent(self.config.get("commentator", {}))
    
    def process(self, input_source: str, mode: str = "auto") -> Dict:
        """
        Process video input through the full pipeline.
        
        Args:
            input_source: YouTube URL, file path, or stream URL
            mode: "youtube", "upload", "live", or "auto" (auto-detect)
            
        Returns:
            Dict with final results including highlight_reel and commentary
        """
        logger.info(f"Starting pipeline processing: {input_source} (mode: {mode})")
        
        results = {
            "input_source": input_source,
            "mode": mode,
            "status": "processing"
        }
        
        try:
            # Step 1: Input Agent - handle video input
            logger.info("Step 1: Processing input...")
            input_result = self.input_agent.process(input_source)
            results["input"] = input_result
            
            # Step 2: Vision Agent - analyze video
            logger.info("Step 2: Analyzing video...")
            vision_result = self.vision_agent.process(input_result)
            results["vision"] = vision_result
            
            # Step 3: Planner Agent - create highlight plan
            logger.info("Step 3: Planning highlights...")
            planner_result = self.planner_agent.process(vision_result)
            results["planner"] = planner_result
            
            # Combine metadata for editor
            editor_input = {
                "plan": planner_result.get("plan", {}),
                "segments": planner_result.get("segments", []),
                "metadata": vision_result.get("metadata", {})
            }
            
            # Step 4: Editor Agent - create highlight reel
            logger.info("Step 4: Editing highlights...")
            editor_result = self.editor_agent.process(editor_input)
            results["editor"] = editor_result
            
            # Combine for commentator
            commentator_input = {
                "plan": planner_result.get("plan", {}),
                "segments": planner_result.get("segments", []),
                "highlight_reel": editor_result.get("highlight_reel")
            }
            
            # Step 5: Commentator Agent - generate commentary
            logger.info("Step 5: Generating commentary...")
            commentary_result = self.commentator_agent.process(commentator_input)
            results["commentary"] = commentary_result
            
            # Final results
            results.update({
                "status": "complete",
                "highlight_reel": editor_result.get("highlight_reel"),
                "commentary_audio": commentary_result.get("audio_file"),
                "commentaries": commentary_result.get("commentaries", []),
                "summary": {
                    "highlights_found": len(planner_result.get("segments", [])),
                    "total_duration": planner_result.get("plan", {}).get("total_duration", 0),
                    "output_file": editor_result.get("highlight_reel")
                }
            })
            
            logger.info("Pipeline processing complete!")
            return results
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            results.update({
                "status": "error",
                "error": str(e)
            })
            return results
    
    def process_live_stream(self, stream_url: str, duration: float = 60) -> Dict:
        """
        Process live stream in real-time.
        
        Args:
            stream_url: RTSP or stream URL
            duration: Duration to process in seconds
            
        Returns:
            Dict with results
        """
        logger.info(f"Processing live stream: {stream_url}")
        
        from handlers.live_stream_handler import LiveStreamHandler
        
        results = {
            "mode": "live",
            "stream_url": stream_url,
            "status": "processing"
        }
        
        try:
            with LiveStreamHandler() as stream_handler:
                if not stream_handler.connect(stream_url):
                    raise RuntimeError("Failed to connect to stream")
                
                # Process stream in chunks
                chunks_processed = 0
                all_detections = []
                all_segments = []
                
                # Calculate number of chunks needed
                from config import CHUNK_DURATION
                num_chunks = int(duration / CHUNK_DURATION) + 1
                
                for chunk_path in stream_handler.process_stream_batch(batch_size=num_chunks):
                    logger.info(f"Processing chunk {chunks_processed + 1}...")
                    
                    # Process chunk through pipeline
                    chunk_result = self.process(str(chunk_path), mode="upload")
                    
                    if chunk_result.get("status") == "complete":
                        all_detections.extend(
                            chunk_result.get("vision", {}).get("events", [])
                        )
                        all_segments.extend(
                            chunk_result.get("planner", {}).get("segments", [])
                        )
                    
                    chunks_processed += 1
                
                # Compile final results from all chunks
                results.update({
                    "status": "complete",
                    "chunks_processed": chunks_processed,
                    "total_detections": len(all_detections),
                    "total_segments": len(all_segments),
                    "detections": all_detections,
                    "segments": all_segments
                })
                
                return results
                
        except Exception as e:
            logger.error(f"Live stream processing error: {e}", exc_info=True)
            results.update({
                "status": "error",
                "error": str(e)
            })
            return results

