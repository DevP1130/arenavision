"""Streamlit frontend for Game Watcher AI."""
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
if "chatbot" not in st.session_state:
    st.session_state.chatbot = ChatbotAgent()
if "iterations" not in st.session_state:
    st.session_state.iterations = []  # List of {iteration_num, video_path, instructions, timestamp}
if "current_iteration" not in st.session_state:
    st.session_state.current_iteration = 0  # Index in iterations list
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_page" not in st.session_state:
    st.session_state.current_page = "editor"  # "editor" or "next_page"


def main():
    """Main Streamlit app."""
    # Check if we should show the next page
    if st.session_state.get("current_page") == "next_page":
        show_next_page()
        return
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
    st.markdown("Generate a logo using Google's WHISK (Imagen) image generation")
    
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
    
    # Continue button (only show if both logo and intro video are selected)
    if st.session_state.selected_image and st.session_state.selected_intro_video:
        st.divider()
        if st.button("➡️ Continue", type="primary", use_container_width=True):
            # Navigate to next page (for now, just show success)
            st.success("✅ Logo and Intro Video selected! Ready to proceed.")
            # TODO: Navigate to next page when implemented
            # st.session_state.current_page = "final"
            # st.rerun()
    
    # Back button
    st.divider()
    if st.button("← Back to Editor"):
        st.session_state.current_page = "editor"
        st.rerun()


if __name__ == "__main__":
    main()
