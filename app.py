"""Streamlit frontend for Game Watcher AI."""
import streamlit as st
import logging
from pathlib import Path
import time

from pipeline import GameWatcherPipeline
from config import OUTPUT_DIR

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Game Watcher AI",
    page_icon="🎥",
    layout="wide"
)

# Initialize session state
if "pipeline" not in st.session_state:
    st.session_state.pipeline = GameWatcherPipeline()
if "results" not in st.session_state:
    st.session_state.results = None
if "processing" not in st.session_state:
    st.session_state.processing = False


def main():
    """Main Streamlit app."""
    st.title("🎥 Game Watcher AI")
    st.markdown("**Intelligent sports highlight generation with agentic AI**")
    
    # Sidebar for mode selection
    st.sidebar.header("⚙️ Input Mode")
    input_mode = st.sidebar.radio(
        "Select input source:",
        ["🎥 YouTube / Upload", "📡 Live Stream"],
        help="Choose how to provide video input"
    )
    
    # Fast mode option
    st.sidebar.header("⚡ Processing Options")
    fast_mode = st.sidebar.checkbox(
        "Fast Mode (Skip Video Intelligence API)",
        value=False,
        help="Faster processing for short videos. Uses only Gemini Vision analysis."
    )
    
    # Main content area
    if input_mode == "🎥 YouTube / Upload":
        youtube_upload_mode(fast_mode)
    else:
        live_stream_mode()
    
    # Display results if available
    if st.session_state.results and st.session_state.results.get("status") == "complete":
        display_results(st.session_state.results)


def youtube_upload_mode(fast_mode: bool = False):
    """YouTube/Upload input mode."""
    st.header("📹 Video Input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("YouTube URL")
        youtube_url = st.text_input(
            "Enter YouTube video URL:",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Paste a YouTube video URL to analyze"
        )
        
        if st.button("Process YouTube Video", type="primary"):
            if youtube_url:
                process_video(youtube_url, mode="youtube", fast_mode=fast_mode)
            else:
                st.error("Please enter a YouTube URL")
    
    with col2:
        st.subheader("Upload Video")
        uploaded_file = st.file_uploader(
            "Upload a video file:",
            type=["mp4", "avi", "mov", "mkv"],
            help="Upload a video file from your computer"
        )
        
        if uploaded_file and st.button("Process Uploaded Video", type="primary"):
            # Save uploaded file
            from config import UPLOAD_DIR
            upload_path = UPLOAD_DIR / uploaded_file.name
            with open(upload_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            process_video(str(upload_path), mode="upload", fast_mode=fast_mode)


def live_stream_mode():
    """Live stream input mode."""
    st.header("📡 Live Stream Input")
    
    stream_url = st.text_input(
        "Enter stream URL:",
        placeholder="rtsp://example.com/stream or http://example.com/stream.m3u8",
        help="Enter RTSP, HLS, or other stream URL"
    )
    
    duration = st.slider(
        "Processing duration (seconds):",
        min_value=10,
        max_value=300,
        value=60,
        step=10,
        help="How long to process the live stream"
    )
    
    if st.button("Start Live Processing", type="primary"):
        if stream_url:
            process_live_stream(stream_url, duration)
        else:
            st.error("Please enter a stream URL")
    
    # Simulate live mode option
    st.info("💡 **Tip**: For demo purposes, you can use a prerecorded video and process it frame-by-frame to simulate live mode.")


def process_video(input_source: str, mode: str, fast_mode: bool = False):
    """Process video through pipeline."""
    st.session_state.processing = True
    st.session_state.results = None
    
    with st.spinner(f"Processing {mode} video... This may take a few minutes."):
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Step 1: Input
            status_text.text("📥 Downloading/loading video...")
            progress_bar.progress(10)
            
            # Configure pipeline for fast mode
            if fast_mode:
                st.session_state.pipeline.vision_agent.use_video_intelligence = False
                status_text.text("⚡ Fast Mode: Using Gemini Vision only (faster!)")
            else:
                st.session_state.pipeline.vision_agent.use_video_intelligence = True
                status_text.text("👁️ Analyzing video content... (Video Intelligence API - may take 1-3 min)")
            
            progress_bar.progress(30)
            
            # Step 3: Planning
            status_text.text("📋 Planning highlights...")
            progress_bar.progress(50)
            
            # Step 4: Editing
            status_text.text("✂️ Creating highlight reel...")
            progress_bar.progress(70)
            
            # Step 5: Commentary
            status_text.text("🎙️ Generating commentary...")
            progress_bar.progress(90)
            
            # Run pipeline (actual processing happens here)
            # Note: Progress bar is approximate - Video Intelligence API is async
            start_time = time.time()
            results = st.session_state.pipeline.process(input_source, mode=mode)
            elapsed = time.time() - start_time
            
            progress_bar.progress(100)
            status_text.text(f"✅ Complete! (Took {elapsed:.1f} seconds)")
            
            st.session_state.results = results
            st.session_state.processing = False
            
            if results.get("status") == "error":
                error_msg = results.get('error', 'Unknown error')
                st.error(f"Error: {error_msg}")
                
                # Provide helpful suggestions for common errors
                if "403" in str(error_msg) or "Forbidden" in str(error_msg):
                    st.warning("""
                    **YouTube Download Issue**: 
                    - Some videos are restricted or age-restricted
                    - Try a different video or use the **Upload** option instead
                    - For hackathon demos, uploading a local video file is more reliable
                    """)
                elif "unable to download" in str(error_msg).lower():
                    st.info("💡 **Tip**: Try using the **Upload Video** option on the right for more reliable processing")
            else:
                st.success(f"Processing complete! Took {elapsed:.1f} seconds. Scroll down to see results.")
                
        except Exception as e:
            st.error(f"Processing failed: {str(e)}")
            st.session_state.processing = False
            logger.error(f"Processing error: {e}", exc_info=True)


def process_live_stream(stream_url: str, duration: float):
    """Process live stream."""
    st.session_state.processing = True
    st.session_state.results = None
    
    with st.spinner(f"Processing live stream for {duration} seconds..."):
        try:
            results = st.session_state.pipeline.process_live_stream(stream_url, duration)
            st.session_state.results = results
            st.session_state.processing = False
            
            if results.get("status") == "error":
                st.error(f"Error: {results.get('error')}")
            else:
                st.success(f"Processed {results.get('chunks_processed', 0)} chunks!")
                
        except Exception as e:
            st.error(f"Live stream processing failed: {str(e)}")
            st.session_state.processing = False


def display_results(results: dict):
    """Display processing results."""
    st.header("📊 Results")
    
    summary = results.get("summary", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Highlights Found", summary.get("highlights_found", 0))
    with col2:
        st.metric("Total Duration", f"{summary.get('total_duration', 0):.1f}s")
    with col3:
        st.metric("Status", "✅ Complete")
    
    # Highlight reel
    highlight_reel = results.get("highlight_reel")
    if highlight_reel and Path(highlight_reel).exists():
        st.subheader("🎬 Highlight Reel")
        st.video(highlight_reel)
        
        # Download button
        with open(highlight_reel, "rb") as f:
            st.download_button(
                label="📥 Download Highlight Reel",
                data=f.read(),
                file_name="highlight_reel.mp4",
                mime="video/mp4"
            )
    
    # Commentary
    commentaries = results.get("commentaries", [])
    if commentaries:
        st.subheader("🎙️ Commentary")
        
        for i, commentary in enumerate(commentaries):
            with st.expander(f"Highlight {i + 1} - {commentary.get('timestamp', 0):.1f}s"):
                st.write(commentary.get("text", ""))
    
    # Commentary audio
    commentary_audio = results.get("commentary_audio")
    if commentary_audio and Path(commentary_audio).exists():
        st.subheader("🔊 Commentary Audio")
        st.audio(commentary_audio)
        
        with open(commentary_audio, "rb") as f:
            st.download_button(
                label="📥 Download Audio",
                data=f.read(),
                file_name="commentary.mp3",
                mime="audio/mpeg"
            )
    
    # Detailed results (expandable)
    with st.expander("🔍 Detailed Results"):
        st.json(results)


if __name__ == "__main__":
    main()
