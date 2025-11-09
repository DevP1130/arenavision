"""Quick demo runner to process a YouTube video through GameWatcherPipeline.

This script runs a single pipeline.process call in fast mode (skip Video Intelligence)
to produce a highlight reel quickly for local testing.
"""
import time
from pipeline import GameWatcherPipeline

def main():
    url = "https://www.youtube.com/watch?v=wgVOgGLtPtc"
    print(f"Starting demo pipeline for: {url}")
    pipeline = GameWatcherPipeline()
    # Use fast mode to skip Video Intelligence heavy calls
    try:
        pipeline.vision_agent.use_video_intelligence = False
    except Exception:
        pass

    start = time.time()
    results = pipeline.process(url, mode="youtube")
    elapsed = time.time() - start

    print(f"Pipeline finished in {elapsed:.1f}s")
    print("Result status:", results.get("status"))
    if results.get("highlight_reel"):
        print("Highlight reel:", results.get("highlight_reel"))
    else:
        print("No highlight reel produced. Check logs for details.")

if __name__ == '__main__':
    main()
