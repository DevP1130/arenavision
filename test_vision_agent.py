"""Test script to verify VisionAgent is working correctly."""
import sys
from pathlib import Path
import json
import warnings

# Apply Python 3.9 compatibility fix before importing anything else
if sys.version_info < (3, 10):
    try:
        import compat_fix  # Apply compatibility shim
    except ImportError:
        pass

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.vision_agent import VisionAgent
from agents.input_agent import InputAgent


def test_vision_agent(video_path: str = None):
    """Test VisionAgent with a video file."""
    print("=" * 60)
    print("🔍 Testing VisionAgent")
    print("=" * 60)
    
    # Initialize VisionAgent
    vision_agent = VisionAgent()
    
    # If no video path provided, try to use existing video
    if not video_path:
        # Check for existing video in uploads
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            video_files = list(uploads_dir.glob("*.mp4"))
            if video_files:
                video_path = str(video_files[0])
                print(f"📹 Using existing video: {video_path}")
            else:
                print("❌ No video file found. Please provide a video path.")
                print("Usage: python test_vision_agent.py <path_to_video.mp4>")
                return
        else:
            print("❌ No video file found. Please provide a video path.")
            print("Usage: python test_vision_agent.py <path_to_video.mp4>")
            return
    
    # Check if video exists
    if not Path(video_path).exists():
        print(f"❌ Video file not found: {video_path}")
        return
    
    print(f"\n📹 Video: {video_path}")
    print(f"🎯 Testing VisionAgent analysis...\n")
    
    # Test with InputAgent first to get proper format
    print("Step 1: Processing input...")
    input_agent = InputAgent()
    try:
        input_result = input_agent.process(video_path)
        print(f"✅ Input processed: {input_result.get('status')}")
        print(f"   Mode: {input_result.get('mode')}")
        print(f"   Video path: {input_result.get('video_path')}\n")
    except Exception as e:
        print(f"⚠️  Input processing error: {e}")
        # Continue with direct video path
        input_result = {"video_path": video_path, "mode": "upload"}
    
    # Test VisionAgent
    print("Step 2: Running VisionAgent analysis...")
    print("-" * 60)
    
    try:
        # Test with Video Intelligence API
        print("\n🔬 Testing Video Intelligence API...")
        vision_agent.use_video_intelligence = True
        vision_agent.use_gemini_vision = False  # Test one at a time
        
        result_vi = vision_agent.process(input_result)
        
        print(f"✅ Video Intelligence API: SUCCESS")
        print(f"   Key frames detected: {len(result_vi.get('key_frames', []))}")
        print(f"   Plays detected: {len(result_vi.get('plays', []))}")
        
        if result_vi.get('key_frames'):
            print(f"\n   Sample key frames:")
            for i, kf in enumerate(result_vi.get('key_frames', [])[:3]):
                print(f"     {i+1}. Time: {kf.get('start_time', 0):.1f}s - {kf.get('end_time', 0):.1f}s")
        
        if result_vi.get('plays'):
            print(f"\n   Sample plays:")
            for i, play in enumerate(result_vi.get('plays', [])[:3]):
                print(f"     {i+1}. {play.get('label', 'Unknown')} at {play.get('start_time', 0):.1f}s (confidence: {play.get('confidence', 0):.2f})")
        
    except Exception as e:
        print(f"❌ Video Intelligence API: FAILED")
        print(f"   Error: {e}")
        import traceback
        error_type = type(e).__name__
        if "importlib.metadata" in str(e) or "packages_distributions" in str(e):
            print(f"\n   ⚠️  This is a Python 3.9 compatibility issue with Google Cloud libraries.")
            print(f"   💡 Solution: Try using Fast Mode (Gemini Vision only) or upgrade to Python 3.10+")
            print(f"   💡 You can disable Video Intelligence API and use only Gemini Vision:")
            print(f"      vision_agent.use_video_intelligence = False")
        print(f"\n   Full error traceback:")
        traceback.print_exc()
    
    # Test with Gemini Vision
    print("\n" + "-" * 60)
    print("\n👁️  Testing Gemini Vision...")
    vision_agent.use_video_intelligence = False
    vision_agent.use_gemini_vision = True
    
    try:
        result_gemini = vision_agent.process(input_result)
        
        print(f"✅ Gemini Vision: SUCCESS")
        print(f"   Events detected: {len(result_gemini.get('events', []))}")
        
        if result_gemini.get('events'):
            print(f"\n   Sample events:")
            for i, event in enumerate(result_gemini.get('events', [])[:5]):
                print(f"     {i+1}. Time: {event.get('timestamp', 0):.1f}s")
                print(f"        Successful: {event.get('is_successful', False)}")
                print(f"        Highlight: {event.get('is_highlight', False)}")
                print(f"        Crowd reaction: {event.get('crowd_reaction', 0)}/10")
                print(f"        Player visible: {event.get('player_visible', False)}")
                if event.get('analysis'):
                    analysis_preview = event.get('analysis', '')[:100]
                    print(f"        Analysis: {analysis_preview}...")
                print()
        
    except Exception as e:
        print(f"❌ Gemini Vision: FAILED")
        print(f"   Error: {e}")
        import traceback
        print(f"\n   Full error traceback:")
        traceback.print_exc()
    
    # Test with both enabled
    print("\n" + "-" * 60)
    print("\n🚀 Testing Full VisionAgent (both APIs)...")
    vision_agent.use_video_intelligence = True
    vision_agent.use_gemini_vision = True
    
    try:
        result_full = vision_agent.process(input_result)
        
        print(f"✅ Full Analysis: SUCCESS")
        print(f"\n📊 Summary:")
        print(f"   Key frames: {len(result_full.get('key_frames', []))}")
        print(f"   Plays: {len(result_full.get('plays', []))}")
        print(f"   Events: {len(result_full.get('events', []))}")
        print(f"   Total detections: {len(result_full.get('key_frames', [])) + len(result_full.get('plays', [])) + len(result_full.get('events', []))}")
        
        # Save results to file
        output_file = Path("outputs") / "vision_agent_test_results.json"
        output_file.parent.mkdir(exist_ok=True)
        
        # Prepare JSON-serializable results
        json_results = {
            "video_path": video_path,
            "key_frames_count": len(result_full.get('key_frames', [])),
            "plays_count": len(result_full.get('plays', [])),
            "events_count": len(result_full.get('events', [])),
            "sample_key_frames": result_full.get('key_frames', [])[:5],
            "sample_plays": result_full.get('plays', [])[:5],
            "sample_events": [
                {
                    "timestamp": e.get('timestamp'),
                    "is_successful": e.get('is_successful'),
                    "is_highlight": e.get('is_highlight'),
                    "crowd_reaction": e.get('crowd_reaction'),
                    "player_visible": e.get('player_visible'),
                    "analysis_preview": e.get('analysis', '')[:200] if e.get('analysis') else None
                }
                for e in result_full.get('events', [])[:5]
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
    except Exception as e:
        print(f"❌ Full Analysis: FAILED")
        print(f"   Error: {e}")
        import traceback
        error_type = type(e).__name__
        if "importlib.metadata" in str(e) or "packages_distributions" in str(e):
            print(f"\n   ⚠️  Python 3.9 compatibility issue detected.")
            print(f"   💡 Recommendation: Use Gemini Vision only (Fast Mode)")
            print(f"   💡 Or upgrade to Python 3.10+ for full Video Intelligence support")
        print(f"\n   Full error traceback:")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ VisionAgent test complete!")
    print("=" * 60)


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else None
    test_vision_agent(video_path)

