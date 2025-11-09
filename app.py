"""Streamlit frontend for ArenaVision."""
# Apply Python 3.9 compatibility fix before importing Google Cloud libraries
import sys
if sys.version_info < (3, 10):
    try:
        import compat_fix  # Apply compatibility shim
    except ImportError:
        pass

import streamlit as st
import logging
from pathlib import Path
import time

from pipeline import GameWatcherPipeline
from config import OUTPUT_DIR
from agents.chatbot_agent import ChatbotAgent
from utils.video_editor import apply_editing_instructions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="ArenaVision",
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
if "chatbot" not in st.session_state:
    st.session_state.chatbot = ChatbotAgent()
if "iterations" not in st.session_state:
    st.session_state.iterations = []  # List of {iteration_num, video_path, instructions, timestamp}
if "current_iteration" not in st.session_state:
    st.session_state.current_iteration = 0  # Index in iterations list
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "editor"  # "editor" -> editing, "next_page" -> logo/intro, "final" -> final output
if "skip_logo" not in st.session_state:
    st.session_state.skip_logo = False
if "skip_intro" not in st.session_state:
    st.session_state.skip_intro = False

# Sidebar brand/logo (attempt background removal of white)
def _sidebar_brand_logo():
    """Render the brand logo in the sidebar, falling back to text if missing.

    Tries to remove white background when PIL/NumPy available; otherwise shows raw logo.
    """
    from config import BASE_DIR, TEMP_DIR
    logo_path = BASE_DIR / "logo.jpeg"
    if not logo_path.exists():
        st.sidebar.markdown("### ArenaVision")
        return

    # Try to show logo with background removal; if that fails, show raw image.
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(logo_path).convert("RGBA")
        arr = np.array(img)
        r, g, b, a = arr.T
        white_mask = (r > 240) & (g > 240) & (b > 240)
        arr[..., 3][white_mask] = 0
        out = Image.fromarray(arr)
        temp_logo = TEMP_DIR / "brand_logo.png"
        out.save(temp_logo)
        st.sidebar.image(str(temp_logo), use_container_width=True)
    except Exception:
        st.sidebar.image(str(logo_path), use_container_width=True)


def main():
    """Main Streamlit app."""
    # Check if we should show the next/final page
    if st.session_state.get("current_page") == "next_page":
        show_next_page()
        return
    if st.session_state.get("current_page") == "final":
        show_final_page()
        return
    _sidebar_brand_logo()
    # Header with top-left logo and title on first page
    try:
        from config import BASE_DIR, TEMP_DIR
        logo_file = None
        processed = (TEMP_DIR / "brand_logo.png")
        if processed.exists():
            logo_file = processed
        else:
            raw_logo = BASE_DIR / "logo.jpeg"
            if raw_logo.exists():
                logo_file = raw_logo
        if logo_file is not None:
            col_logo, col_title = st.columns([1, 8])
            with col_logo:
                st.image(str(logo_file), use_container_width=True)
            with col_title:
                st.title("🎥 ArenaVision")
                st.markdown("**Intelligent sports highlight generation with agentic AI**")
        else:
            st.title("🎥 ArenaVision")
            st.markdown("**Intelligent sports highlight generation with agentic AI**")
    except Exception:
        st.title("🎥 ArenaVision")
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
    # Reset iterations when processing new video
    st.session_state.iterations = []
    st.session_state.current_iteration = 0
    st.session_state.chat_history = []
    
    with st.spinner(f"Processing {mode} video... This may take a few minutes."):
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            percent_text = st.empty()
            
            # Configure pipeline for fast mode
            if fast_mode:
                st.session_state.pipeline.vision_agent.use_video_intelligence = False
            else:
                st.session_state.pipeline.vision_agent.use_video_intelligence = True
            
            # Progress callback function
            def update_progress(percent: int, message: str):
                """Update progress bar and status text."""
                progress_bar.progress(percent / 100.0)
                status_text.text(message)
                percent_text.markdown(f"**{percent}%**")
            
            # Run pipeline with progress callback
            start_time = time.time()
            results = st.session_state.pipeline.process(
                input_source, 
                mode=mode,
                progress_callback=update_progress
            )
            elapsed = time.time() - start_time
            
            # Final update
            progress_bar.progress(1.0)
            status_text.text(f"✅ Complete! (Took {elapsed:.1f} seconds)")
            percent_text.markdown("**100%**")
            
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
            elif results.get("status") == "no_highlights":
                st.warning("⚠️ No highlights detected")
                st.info(results.get("message", "No highlight-worthy moments found. Try a different video or enable more detection features."))
                st.info("💡 **Tips**: Try disabling Fast Mode to use Video Intelligence API, or use a video with more clear scoring plays.")
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
    """Display processing results with chatbot editing interface."""
    # Only show if we have a valid highlight reel
    highlight_reel = results.get("highlight_reel")
    if not highlight_reel or not Path(highlight_reel).exists():
        st.warning("No highlight reel available yet. Please process a video first.")
        return
    
    st.header("📊 Results")
    
    summary = results.get("summary", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Highlights Found", summary.get("highlights_found", 0))
    with col2:
        st.metric("Total Duration", f"{summary.get('total_duration', 0):.1f}s")
    with col3:
        st.metric("Status", "✅ Complete")
    
    # Initialize iterations with original highlight reel (only once)
    if highlight_reel and Path(highlight_reel).exists() and len(st.session_state.iterations) == 0:
        st.session_state.iterations.append({
            "iteration_num": 0,
            "video_path": highlight_reel,
            "instructions": "Original highlight reel",
            "timestamp": time.time()
        })
        st.session_state.current_iteration = 0
    
    # Main layout: 2/3 video, 1/3 chatbot
    col_video, col_chat = st.columns([2, 1])
    
    with col_video:
        st.subheader("🎬 Highlight Reel Editor")
        
        # Iteration navigation (slideshow)
        iterations = st.session_state.iterations
        if len(iterations) > 1:
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            with col_prev:
                prev_clicked = st.button("◀ Previous", disabled=st.session_state.current_iteration == 0, key="prev_iter")
                if prev_clicked:
                    st.session_state.current_iteration = max(0, st.session_state.current_iteration - 1)
                    st.rerun()
            with col_info:
                st.info(f"Iteration {st.session_state.current_iteration + 1} of {len(iterations)}")
            with col_next:
                next_clicked = st.button("Next ▶", disabled=st.session_state.current_iteration >= len(iterations) - 1, key="next_iter")
                if next_clicked:
                    st.session_state.current_iteration = min(len(iterations) - 1, st.session_state.current_iteration + 1)
                    st.rerun()
        
        # Display current iteration video
        if iterations and len(iterations) > 0:
            current_iter = iterations[st.session_state.current_iteration] if st.session_state.current_iteration < len(iterations) else iterations[0]
            if current_iter and Path(current_iter["video_path"]).exists():
                st.video(current_iter["video_path"])
                st.caption(f"**{current_iter['instructions']}**")
            else:
                st.warning("Video file not found for current iteration")
        elif highlight_reel and Path(highlight_reel).exists():
            st.video(highlight_reel)
            st.caption("**Original highlight reel**")
        else:
            st.warning("No video available")
        
        # Continue button to go to next page
        if iterations:
            current_iter = iterations[st.session_state.current_iteration] if st.session_state.current_iteration < len(iterations) else iterations[0]
            if current_iter and Path(current_iter["video_path"]).exists():
                st.subheader("➡️ Continue")
                if st.button("Continue", type="primary", key="continue_button"):
                    st.session_state.current_page = "next_page"
                    st.rerun()
    
    with col_chat:
        st.subheader("🤖 Video Editing Chatbot")
        
        # Show video context info
        with st.expander("📋 Video Context", expanded=False):
            st.write("**Available Data:**")
            vision_data = results.get("vision", {})
            planner_data = results.get("planner", {})
            st.write(f"- Events: {len(vision_data.get('events', []))}")
            st.write(f"- Plays: {len(vision_data.get('plays', []))}")
            st.write(f"- Segments: {len(planner_data.get('segments', []))}")
            st.write(f"- Commentaries: {len(results.get('commentaries', []))}")
        
        # Clip selection for context
        clips = results.get("clips", [])
        if clips:
            st.write("**Select clips as context:**")
            selected_clips = st.multiselect(
                "Choose clips to reference:",
                options=clips,
                format_func=lambda x: Path(x).name,
                key="context_clips"
            )
        else:
            selected_clips = []
        
        # Chat history display
        if st.session_state.chat_history:
            st.write("**Chat History:**")
            for msg in st.session_state.chat_history[-5:]:  # Show last 5 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")[:100]
                if role == "user":
                    st.write(f"👤 **You:** {content}...")
                else:
                    st.write(f"🤖 **Bot:** {content}...")
        
        # Chat input
        user_message = st.text_area(
            "Describe how you want to edit the video:",
            placeholder="e.g., 'Make it faster', 'Remove the first segment', 'Add slow motion to scoring plays'",
            key="chat_input",
            height=100
        )
        
        if st.button("✏️ Apply Edit", type="primary"):
            if user_message:
                with st.spinner("Processing your request..."):
                    # Prepare video data for chatbot
                    vision_data = results.get("vision", {})
                    planner_data = results.get("planner", {})
                    video_data = {
                        "metadata": vision_data.get("metadata", {}),
                        "events": vision_data.get("events", []),
                        "plays": vision_data.get("plays", []),
                        "key_frames": vision_data.get("key_frames", []),
                        "segments": planner_data.get("segments", []),
                        "commentaries": results.get("commentaries", [])
                    }
                    
                    # Get editing instructions from chatbot
                    edit_result = st.session_state.chatbot.process_edit_request(
                        user_message,
                        video_data,
                        selected_clips
                    )
                    
                    if edit_result.get("status") == "success":
                        instructions = edit_result.get("editing_instructions")
                        
                        # Apply editing instructions
                        # For segment removal/editing, we need the original video, not the highlight reel
                        # Check if we need to use original video (for segment operations)
                        action = instructions.get("action", "")
                        
                        # Try multiple paths to find original video
                        original_video_path = (
                            results.get("vision", {}).get("metadata", {}).get("video_path") or
                            results.get("input", {}).get("video_path") or
                            results.get("video_path")
                        )
                        
                        # Use original video if editing segments, otherwise use current iteration
                        if action == "edit_segment" and original_video_path and Path(original_video_path).exists():
                            source_video = original_video_path
                            st.info(f"🔧 Using original video for segment editing: {Path(original_video_path).name}")
                        else:
                            source_video = current_iter["video_path"] if current_iter else highlight_reel
                            if action == "edit_segment":
                                st.warning(f"⚠️ Could not find original video, using highlight reel instead. Segment removal may not work correctly.")
                        
                        if source_video and Path(source_video).exists():
                            try:
                                planner_data = results.get("planner", {})
                                new_video_path = apply_editing_instructions(
                                    source_video,
                                    instructions,
                                    planner_data.get("segments", [])
                                )
                                
                                # Add to iterations
                                new_iteration = {
                                    "iteration_num": len(iterations),
                                    "video_path": new_video_path,
                                    "instructions": user_message,
                                    "timestamp": time.time()
                                }
                                st.session_state.iterations.append(new_iteration)
                                st.session_state.current_iteration = len(st.session_state.iterations) - 1
                                
                                # Add to chat history
                                st.session_state.chat_history.append({
                                    "role": "user",
                                    "content": user_message
                                })
                                st.session_state.chat_history.append({
                                    "role": "assistant",
                                    "content": f"Applied: {instructions.get('instructions', 'Edit completed')}"
                                })
                                
                                st.success("✅ Edit applied! View the new iteration above.")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error applying edit: {str(e)}")
                        else:
                            st.error("No video available to edit")
                    elif edit_result.get("status") == "api_key_error":
                        error_msg = edit_result.get("error", "API key issue")
                        st.error(f"🔐 {error_msg}")
                        st.warning("**Action Required:**")
                        st.markdown("""
                        1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
                        2. Delete the old API key (if it shows as leaked)
                        3. Create a new API key
                        4. Update your `.env` file with the new key:
                           ```
                           GOOGLE_API_KEY=your_new_api_key_here
                           ```
                        5. Restart the Streamlit server
                        """)
                    elif edit_result.get("status") == "quota_error":
                        error_msg = edit_result.get("error", "API quota exceeded")
                        st.error(f"⚠️ {error_msg}")
                        st.info("💡 **Tip**: The chatbot will automatically retry with a model that has higher quotas. Please wait a moment and try again.")
                    else:
                        error_msg = edit_result.get("error", "Unknown error")
                        st.error(f"Error: {error_msg}")
                        if "quota" in error_msg.lower() or "429" in error_msg:
                            st.info("💡 **Tip**: You've hit the API quota limit. The system will try to use a model with higher quotas on the next request.")
                        elif "403" in error_msg or "leaked" in error_msg.lower() or "api key" in error_msg.lower():
                            st.warning("🔐 **API Key Issue**: Your API key may have been reported as leaked. Please generate a new one from [Google AI Studio](https://aistudio.google.com/app/apikey)")
            else:
                st.warning("Please enter an editing request")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()
    
    # Mini clips section (below main layout)
    clips = results.get("clips", [])
    commentaries = results.get("commentaries", [])
    
    if clips:
        st.subheader("📹 Individual Video Segments")
        st.write("View and download individual highlight segments:")
        
        # Display clips in a grid
        num_cols = 3
        for i in range(0, len(clips), num_cols):
            cols = st.columns(num_cols)
            for j, col in enumerate(cols):
                clip_idx = i + j
                if clip_idx < len(clips):
                    clip_path = clips[clip_idx]
                    with col:
                        if Path(clip_path).exists():
                            st.video(clip_path)
                            clip_name = Path(clip_path).name
                            
                            # Show commentary if available
                            if clip_idx < len(commentaries):
                                comm = commentaries[clip_idx]
                                st.caption(f"**Segment {clip_idx + 1}** - {comm.get('text', '')[:60]}...")
                                st.caption(f"Timestamp: {comm.get('timestamp', 0):.1f}s")
                            else:
                                st.caption(f"**Segment {clip_idx + 1}** - {clip_name}")
                            
                            # Download button for each clip
                            with open(clip_path, "rb") as f:
                                st.download_button(
                                    label=f"📥 Download Segment {clip_idx + 1}",
                                    data=f.read(),
                                    file_name=clip_name,
                                    mime="video/mp4",
                                    key=f"download_segment_{clip_idx}"
                                )
                        else:
                            st.warning(f"Clip {clip_idx + 1} not found")
    
    # Commentary audio (below clips)
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


def show_next_page():
    """Show the logo generation page with WHISK/Imagen."""
    st.title("🎨 Logo Generation")
    st.markdown("Generate a logo using Google's WHISK (Imagen) image generation or upload your own logo.")
    
    # Initialize session state for image generation
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = []
    if "selected_image" not in st.session_state:
        st.session_state.selected_image = None
    if "logo_prompt" not in st.session_state:
        st.session_state.logo_prompt = ""
    
    # Prompt input
    st.subheader("📝 Describe Your Logo")
    prompt = st.text_input(
        "Enter a description of the logo you want to generate:",
        value=st.session_state.logo_prompt,
        placeholder="e.g., 'A modern basketball logo with a basketball and lightning bolt, blue and orange colors, minimalist design'",
        key="logo_prompt_input"
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        generate_button = st.button("✨ Generate Logo", type="primary", use_container_width=True)
    
    with col2:
        if st.button("🔄 Reprompt", use_container_width=True):
            st.session_state.generated_images = []
            st.session_state.selected_image = None
            st.rerun()

    # Upload a logo instead of generating
    st.subheader("📤 Upload a Logo")
    uploaded_logo = st.file_uploader(
        "Upload a PNG/JPG logo (transparent recommended):",
        type=["png", "jpg", "jpeg"],
        key="logo_uploader",
        help="If provided, this will be used instead of generating a logo."
    )
    if uploaded_logo is not None:
        from config import OUTPUT_DIR
        from PIL import Image
        upload_dir = OUTPUT_DIR / "generated_images"
        upload_dir.mkdir(parents=True, exist_ok=True)
        save_path = upload_dir / f"uploaded_logo_{int(time.time())}.png"
        Image.open(uploaded_logo).convert("RGBA").save(save_path)
        st.session_state.selected_image = {"image_path": str(save_path), "source": "uploaded"}
        st.success("✅ Logo uploaded and selected")
    
    # Generate images
    if generate_button and prompt:
        st.session_state.logo_prompt = prompt
        with st.spinner("🎨 Generating logo variations... This may take a moment."):
            from utils.image_generator import generate_logo_images
            generated = generate_logo_images(prompt, num_images=3)
            st.session_state.generated_images = generated
    
    # Display generated images
    if st.session_state.generated_images:
        st.subheader("🖼️ Generated Logo Options")
        st.write("Select one of the generated logos:")
        
        # Filter out None values
        valid_images = [img for img in st.session_state.generated_images if img is not None]
        
        if valid_images:
            # Display images in 3 columns
            cols = st.columns(3)
            
            for idx, img_data in enumerate(valid_images[:3]):
                with cols[idx]:
                    if img_data and "image_path" in img_data:
                        image_path = Path(img_data["image_path"])
                        if image_path.exists():
                            st.image(str(image_path), caption=f"Option {idx + 1}", use_container_width=True)
                            
                            # Check if this image is selected
                            is_selected = (st.session_state.selected_image and 
                                         st.session_state.selected_image.get("index") == img_data.get("index"))
                            
                            # Selection button with green color if selected
                            button_label = f"✓ Selected" if is_selected else f"Select Option {idx + 1}"
                            button_type = "primary" if is_selected else "secondary"
                            
                            if st.button(button_label, key=f"select_{idx}", use_container_width=True, type=button_type):
                                st.session_state.selected_image = img_data
                                st.toast(f"✅ Selected Option {idx + 1}!", icon="✅")
                                st.rerun()
                        else:
                            st.warning(f"Image {idx + 1} not found")
                    else:
                        st.warning(f"Option {idx + 1} generation failed")
        else:
            st.error("❌ No images were generated. Please try a different prompt or check your API configuration.")
            
            # Show helpful error information
            with st.expander("🔧 Troubleshooting"):
                st.write("**Common issues:**")
                st.write("1. **Vertex AI API not enabled**: Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Enable 'Vertex AI API'")
                st.write("2. **Imagen API not available**: Imagen may require special access. Check if it's enabled in your project.")
                st.write("3. **Service account permissions**: Ensure your service account has 'Vertex AI User' role")
                st.write("4. **Billing enabled**: Imagen may require billing to be enabled on your Google Cloud project")
                st.write("5. **Project ID**: Check that `GOOGLE_CLOUD_PROJECT` in your `.env` file is correct")
                
                from config import GOOGLE_CLOUD_PROJECT
                if GOOGLE_CLOUD_PROJECT:
                    st.write(f"**Current Project ID**: `{GOOGLE_CLOUD_PROJECT}`")
                else:
                    st.error("⚠️ `GOOGLE_CLOUD_PROJECT` is not set in your `.env` file")
    
    # Show download button for selected image (small, not large display)
    if st.session_state.selected_image:
        selected = st.session_state.selected_image
        if selected and "image_path" in selected:
            image_path = Path(selected["image_path"])
            if image_path.exists():
                # Small download section
                st.divider()
                st.write("**Selected Logo Ready**")
                with open(image_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Selected Logo",
                        data=f.read(),
                        file_name=f"logo_{hash(st.session_state.logo_prompt) % 10000}.png",
                        mime="image/png",
                        key="download_logo",
                        use_container_width=True
                    )
    
    # Skip only the logo step (continue to intro generation)
    st.divider()
    if st.button("⏭️ Skip Logo", key="skip_logo", use_container_width=True):
        st.session_state.skip_logo = True
        st.toast("Skipped logo step", icon="⏭️")
        st.rerun()

    # Veo Intro Video Generation Section
    st.divider()
    st.subheader("🎬 Intro Video Generation")
    st.markdown("Generate a 5-second intro video using Veo 3.0")
    
    # Initialize session state for intro video
    if "intro_videos" not in st.session_state:
        st.session_state.intro_videos = []
    if "selected_intro_video" not in st.session_state:
        st.session_state.selected_intro_video = None
    if "intro_text" not in st.session_state:
        st.session_state.intro_text = ""
    if "intro_background" not in st.session_state:
        st.session_state.intro_background = ""
    
    # Get video summary from results for default text
    video_summary = ""
    if st.session_state.results:
        # Try to get summary from commentator's narration
        commentary = st.session_state.results.get("commentary", {})
        if commentary and commentary.get("overall_narration"):
            video_summary = commentary.get("overall_narration", "")
        # Fallback: create summary from highlights
        elif st.session_state.results.get("summary"):
            summary = st.session_state.results.get("summary", {})
            highlights = summary.get("highlights_found", 0)
            duration = summary.get("total_duration", 0)
            video_summary = f"Watch the top {highlights} highlights from this {duration:.0f} second game!"
    
    # Two separate inputs
    col_text, col_bg = st.columns(2)
    
    with col_text:
        st.write("**📝 Text to Display**")
        intro_text = st.text_input(
            "Enter text to display on video (centered):",
            value=st.session_state.intro_text or video_summary or "Game Highlights",
            placeholder="e.g., 'Game Highlights' or 'Top Plays'",
            key="intro_text_input",
            help="This text will be centered on the video"
        )
    
    with col_bg:
        st.write("**🎨 Background Description**")
        intro_background = st.text_input(
            "Describe the background style:",
            value=st.session_state.intro_background or "dark blue gradient with animated particles",
            placeholder="e.g., 'dark blue gradient', 'bright energetic', 'red fire theme'",
            key="intro_background_input",
            help="Describe the visual style of the background (colors, theme, effects)"
        )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        generate_video_button = st.button("✨ Generate Intro Video", type="primary", use_container_width=True)
    
    with col2:
        if st.button("🔄 Regenerate", use_container_width=True):
            st.session_state.intro_videos = []
            st.session_state.selected_intro_video = None
            st.rerun()
    
    # Generate intro videos
    if generate_video_button and intro_text and intro_background:
        st.session_state.intro_text = intro_text
        st.session_state.intro_background = intro_background
        with st.spinner("🎬 Generating intro video with Veo 3.0... This may take a few minutes."):
            from utils.veo_generator import generate_intro_video
            
            # Get logo path if selected
            logo_path = None
            if st.session_state.selected_image and st.session_state.selected_image.get("image_path"):
                logo_path = st.session_state.selected_image.get("image_path")
            
            # Generate 3 variations
            generated_videos = []
            for i in range(3):
                video_result = generate_intro_video(
                    text=intro_text,
                    background_description=intro_background,
                    max_duration=5,
                    logo_path=logo_path
                )
                if video_result:
                    video_result["index"] = i
                    generated_videos.append(video_result)
                else:
                    generated_videos.append(None)
            
            st.session_state.intro_videos = generated_videos
    
    # Display generated intro videos
    if st.session_state.intro_videos:
        st.subheader("🎥 Generated Intro Video Options")
        st.write("Select one of the generated intro videos:")
        
        # Filter out None values
        valid_videos = [vid for vid in st.session_state.intro_videos if vid is not None]
        
        if valid_videos:
            # Display videos in 3 columns
            cols = st.columns(3)
            
            for idx, vid_data in enumerate(valid_videos[:3]):
                with cols[idx]:
                    if vid_data and "video_path" in vid_data:
                        video_path = Path(vid_data["video_path"])
                        if video_path.exists():
                            st.video(str(video_path))
                            
                            # Check if this video is selected
                            is_selected = (st.session_state.selected_intro_video and 
                                         st.session_state.selected_intro_video.get("index") == vid_data.get("index"))
                            
                            # Selection button with green color if selected
                            button_label = f"✓ Selected" if is_selected else f"Select Option {idx + 1}"
                            button_type = "primary" if is_selected else "secondary"
                            
                            if st.button(button_label, key=f"select_video_{idx}", use_container_width=True, type=button_type):
                                st.session_state.selected_intro_video = vid_data
                                st.toast(f"✅ Selected Intro Video {idx + 1}!", icon="✅")
                                st.rerun()
                        else:
                            st.warning(f"Video {idx + 1} not found")
                    else:
                        st.warning(f"Option {idx + 1} generation failed")
        else:
            st.error("❌ No intro videos were generated. Please try again or check your API configuration.")
    
    # Show download button for selected intro video
    if st.session_state.selected_intro_video:
        selected = st.session_state.selected_intro_video
        if selected and "video_path" in selected:
            video_path = Path(selected["video_path"])
            if video_path.exists():
                st.divider()
                st.write("**Selected Intro Video Ready**")
                with open(video_path, "rb") as f:
                    st.download_button(
                        label="📥 Download Selected Intro Video",
                        data=f.read(),
                        file_name=f"intro_{hash(st.session_state.intro_prompt) % 10000}.mp4",
                        mime="video/mp4",
                        key="download_intro_video",
                        use_container_width=True
                    )
    
    # Continue button (logo optional; allow continue if intro video selected)
    if st.session_state.selected_intro_video:
        st.divider()
        if st.button("➡️ Continue", type="primary", use_container_width=True):
            # Navigate to final page
            st.session_state.current_page = "final"
            st.rerun()

    # Skip intro button: allow users to go straight to final/download/twitter page
    st.divider()
    if st.button("⏭️ Skip Intro and Go to Final", key="skip_intro_and_final", use_container_width=True):
        # Keep selected_intro_video as-is (may be None). Final page will handle missing video gracefully.
        st.session_state.skip_intro = True
        st.session_state.current_page = "final"
        st.rerun()
    
    # Back button
    st.divider()
    if st.button("← Back to Editor"):
        st.session_state.current_page = "editor"
        st.rerun()


def show_final_page():
    """Show the final composed video with download and post-to-X options."""
    st.title("✅ Final Video")
    st.markdown("Review your final video and post it to X (Twitter) if you want.")

    # Navigation: Back to previous screen (Logo/Intro page)
    nav_col, _ = st.columns([1, 8])
    with nav_col:
        if st.button("← Back", key="back_to_previous_final"):
            st.session_state.current_page = "next_page"  # Go back to the previous (branding) step
            st.rerun()

    # Determine which video to show on the final page.
    # New priority: latest editor iteration (current or last) -> selected intro video -> pipeline highlight reel
    video_path = None
    video_source = None

    # 1) Latest iteration from editor page
    iterations = st.session_state.get("iterations", [])
    if iterations and isinstance(iterations, list):
        # Prefer the currently selected iteration index if valid; otherwise use the last available
        idx = st.session_state.get("current_iteration", len(iterations) - 1)
        if not isinstance(idx, int) or idx < 0 or idx >= len(iterations):
            idx = len(iterations) - 1

        candidate = iterations[idx].get("video_path") if iterations[idx] else None
        # If the current one doesn't exist on disk, fall back to the most recent existing one
        if not candidate or not Path(candidate).exists():
            for it in reversed(iterations):
                cand = it.get("video_path") if it else None
                if cand and Path(cand).exists():
                    candidate = cand
                    break
        if candidate and Path(candidate).exists():
            video_path = Path(candidate)
            video_source = "iteration"

    # 2) Selected intro video (if no editor iteration is available)
    if video_path is None:
        selected = st.session_state.get("selected_intro_video")
        if selected and "video_path" in selected and Path(selected["video_path"]).exists():
            video_path = Path(selected["video_path"])
            video_source = "intro"

    # 3) Pipeline results' highlight reel as last fallback
    if video_path is None:
        results = st.session_state.get("results") or {}
        highlight = results.get("highlight_reel") if results else None
        if highlight and Path(highlight).exists():
            video_path = Path(highlight)
            video_source = "highlight_reel"

    if video_path is None:
        st.error("Final video not found. Go back and generate or select a video first.")
        # Offer quick navigation back to branding step to resolve missing video
        if st.button("← Back to Branding", key="back_no_video_branding"):
            st.session_state.current_page = "next_page"
            st.rerun()
        # Also allow going straight back to Editor if desired
        if st.button("← Back to Editor", key="back_no_video_editor"):
            st.session_state.current_page = "editor"
            st.rerun()
        return

    st.subheader("🎬 Final Video")
    # If a logo is selected or uploaded, overlay it bottom-right on a cached output
    overlay_candidate = None
    try:
        selected_logo = st.session_state.get("selected_image")
        if selected_logo and selected_logo.get("image_path") and Path(selected_logo["image_path"]).exists():
            from utils.video_utils import overlay_logo_on_video
            # Fixed smaller size (no sliders)
            overlay_candidate = overlay_logo_on_video(
                video_path=video_path,
                logo_path=Path(selected_logo["image_path"]),
                position=("right", "bottom"),
                scale=0.10,  # smaller than previous 0.15
                margin=30,
            )
    except Exception:
        overlay_candidate = None

    st.video(str(overlay_candidate or video_path))

    # Download button
    with open(video_path, "rb") as f:
        video_bytes = f.read()
        st.download_button(
            label="📥 Download Final Video",
            data=video_bytes,
            file_name=video_path.name,
            mime="video/mp4",
            key="download_final_video"
        )

    st.markdown("---")

    st.subheader("📣 Post to X (Twitter)")
    caption = st.text_area("Caption for X:", value="Check out my new highlights! #ArenaVision")

    if st.button("Post to X", key="post_x"):
        # Attempt to post using OAuth1 to the Twitter API v1.1 media/upload (chunked) + statuses/update
        try:
            from requests_oauthlib import OAuth1Session
            import mimetypes
            import time as _time
            import os
        except Exception:
            st.error("Posting requires the 'requests_oauthlib' package. Install it in the venv: `pip install requests_oauthlib`")
            return

        # Read keys from environment (dotenv loaded in config.py)
        TW_API_KEY = os.getenv("TWITTER_API_KEY")
        TW_API_SECRET = os.getenv("TWITTER_API_SECRET")
        TW_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
        TW_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

        if not all([TW_API_KEY, TW_API_SECRET, TW_ACCESS_TOKEN, TW_ACCESS_SECRET]):
            st.error("Twitter credentials are missing from environment. Add TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_SECRET to your .env")
            return

        # Helper: chunked media upload for videos
        def twitter_upload_video_chunked(oauth: OAuth1Session, path: Path, media_type: str) -> str:
            upload_url = "https://upload.twitter.com/1.1/media/upload.json"
            total_bytes = path.stat().st_size

            # INIT
            init_data = {
                "command": "INIT",
                "total_bytes": str(total_bytes),
                "media_type": media_type,
                "media_category": "tweet_video",
            }
            init_resp = oauth.post(upload_url, data=init_data)
            # Twitter can return 200/201 or 202 (accepted) for INIT
            if init_resp.status_code not in (200, 201, 202):
                raise RuntimeError(f"INIT failed: {init_resp.status_code} {init_resp.text}")
            media_id = init_resp.json().get("media_id_string")
            if not media_id:
                raise RuntimeError("INIT missing media_id_string")

            # APPEND chunks (5MB recommended)
            segment_index = 0
            chunk_size = 5 * 1024 * 1024
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    files = {"media": (path.name, chunk, media_type)}
                    append_data = {
                        "command": "APPEND",
                        "media_id": media_id,
                        "segment_index": str(segment_index),
                    }
                    append_resp = oauth.post(upload_url, data=append_data, files=files)
                    if append_resp.status_code not in (200, 201, 204):
                        raise RuntimeError(f"APPEND failed at segment {segment_index}: {append_resp.status_code} {append_resp.text}")
                    segment_index += 1

            # FINALIZE
            finalize_resp = oauth.post(upload_url, data={"command": "FINALIZE", "media_id": media_id})
            # FINALIZE can respond 200/201 or 202 with processing_info
            if finalize_resp.status_code not in (200, 201, 202):
                raise RuntimeError(f"FINALIZE failed: {finalize_resp.status_code} {finalize_resp.text}")

            # Poll processing if needed
            resp_json = finalize_resp.json()
            processing = resp_json.get("processing_info")
            while processing and processing.get("state") in ("pending", "in_progress"):
                check_after = processing.get("check_after_secs", 3)
                _time.sleep(max(1, int(check_after)))
                status_resp = oauth.get(upload_url, params={"command": "STATUS", "media_id": media_id})
                if status_resp.status_code not in (200, 201):
                    raise RuntimeError(f"STATUS failed: {status_resp.status_code} {status_resp.text}")
                processing = status_resp.json().get("processing_info")
                if processing and processing.get("state") == "failed":
                    err = processing.get("error", {})
                    code = err.get("code")
                    name = err.get("name")
                    msg = err.get("message")
                    raise RuntimeError(f"Media processing failed: {code} {name} {msg}")

            return media_id

        try:
            oauth = OAuth1Session(
                TW_API_KEY,
                client_secret=TW_API_SECRET,
                resource_owner_key=TW_ACCESS_TOKEN,
                resource_owner_secret=TW_ACCESS_SECRET,
            )

            guessed_type, _ = mimetypes.guess_type(str(video_path))
            media_type = guessed_type or "video/mp4"

            # Perform chunked upload to support videos and large files
            media_id = twitter_upload_video_chunked(oauth, video_path, media_type)

            # Create the tweet (try v1.1 first, then fall back to v2 if access limited)
            post_url_v11 = "https://api.twitter.com/1.1/statuses/update.json"
            payload_v11 = {"status": caption, "media_ids": media_id}
            resp2 = oauth.post(post_url_v11, data=payload_v11)
            if resp2.status_code in (200, 201):
                st.success("✅ Posted to X successfully!")
            else:
                # If access is limited to subset endpoints (code 453), fall back to v2 tweet creation
                fallback_to_v2 = False
                try:
                    err_json = resp2.json()
                    errs = err_json.get("errors") or []
                    if errs and isinstance(errs, list) and isinstance(errs[0], dict):
                        if errs[0].get("code") == 453:
                            fallback_to_v2 = True
                except Exception:
                    pass

                if not fallback_to_v2:
                    st.error(f"Failed to post tweet (v1.1): {resp2.status_code} {resp2.text}")
                else:
                    post_url_v2 = "https://api.twitter.com/2/tweets"
                    payload_v2 = {"text": caption, "media": {"media_ids": [media_id]}}
                    resp3 = oauth.post(post_url_v2, json=payload_v2)
                    if resp3.status_code in (200, 201):
                        st.success("✅ Posted to X successfully (v2 endpoint)!")
                    else:
                        st.error(f"Failed to post tweet (v2): {resp3.status_code} {resp3.text}")

        except Exception as e:
            st.error(f"Error posting to X: {e}")


if __name__ == "__main__":
    main()
