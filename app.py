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
if "show_landing" not in st.session_state:
    st.session_state.show_landing = True

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


def show_landing_page():
    """Show the landing/welcome page with camera flash animation."""
    # Hide default Streamlit elements
    hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {
        background: #000000;
    }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # Camera flash animation CSS
    st.markdown("""
    <style>
    @keyframes ballBounce {
        0% {
            opacity: 0;
            transform: translate(-50%, -200%) scale(0.5);
        }
        20% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
        40% {
            transform: translate(-50%, -50%) scale(1);
        }
        45% {
            transform: translate(-50%, -50%) scale(0.9);
        }
        50% {
            transform: translate(-50%, -50%) scale(1.1);
        }
        55% {
            transform: translate(-50%, -50%) scale(1);
        }
        100% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
        }
    }
    
    @keyframes footballBounce {
        0% {
            opacity: 0;
            transform: translate(-60%, -200%) scale(0.5) rotate(0deg);
        }
        20% {
            opacity: 1;
            transform: translate(-60%, -50%) scale(1) rotate(180deg);
        }
        40% {
            transform: translate(-60%, -50%) scale(1) rotate(360deg);
        }
        45% {
            transform: translate(-60%, -50%) scale(0.9) rotate(380deg);
        }
        50% {
            transform: translate(-60%, -50%) scale(1.1) rotate(360deg);
        }
        55% {
            transform: translate(-60%, -50%) scale(1) rotate(340deg);
        }
        100% {
            opacity: 0;
            transform: translate(-60%, -50%) scale(0.8) rotate(180deg);
        }
    }
    
    @keyframes basketballBounce {
        0% {
            opacity: 0;
            transform: translate(-40%, -200%) scale(0.5);
        }
        20% {
            opacity: 1;
            transform: translate(-40%, -50%) scale(1);
        }
        40% {
            transform: translate(-40%, -50%) scale(1);
        }
        45% {
            transform: translate(-40%, -50%) scale(0.9);
        }
        50% {
            transform: translate(-40%, -50%) scale(1.1);
        }
        55% {
            transform: translate(-40%, -50%) scale(1);
        }
        100% {
            opacity: 0;
            transform: translate(-40%, -50%) scale(0.8);
        }
    }
    
    @keyframes stadiumLights {
        0% {
            opacity: 0;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0) 0%, rgba(139, 92, 246, 0) 100%);
        }
        20% {
            opacity: 0.3;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.3) 0%, rgba(139, 92, 246, 0) 70%);
        }
        40% {
            opacity: 0.6;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.6) 0%, rgba(255, 255, 255, 0.4) 30%, rgba(139, 92, 246, 0) 70%);
        }
        45% {
            opacity: 0.8;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.8) 0%, rgba(255, 255, 255, 0.6) 30%, rgba(139, 92, 246, 0) 70%);
        }
        50% {
            opacity: 1;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 1) 0%, rgba(255, 255, 255, 0.8) 30%, rgba(139, 92, 246, 0) 70%);
        }
        55% {
            opacity: 0.8;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.8) 0%, rgba(255, 255, 255, 0.6) 30%, rgba(139, 92, 246, 0) 70%);
        }
        60% {
            opacity: 0.4;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.4) 0%, rgba(139, 92, 246, 0) 70%);
        }
        100% {
            opacity: 0;
            background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0) 0%, rgba(139, 92, 246, 0) 100%);
        }
    }
    
    @keyframes actionLines {
        0% {
            opacity: 0;
            transform: translateX(-100px) scaleX(0);
        }
        40% {
            opacity: 0;
            transform: translateX(-100px) scaleX(0);
        }
        45% {
            opacity: 0.8;
            transform: translateX(0) scaleX(1);
        }
        55% {
            opacity: 0.8;
            transform: translateX(0) scaleX(1);
        }
        60% {
            opacity: 0;
            transform: translateX(100px) scaleX(0);
        }
        100% {
            opacity: 0;
            transform: translateX(100px) scaleX(0);
        }
    }
    
    @keyframes logoFadeIn {
        0% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
        }
        45% {
            opacity: 0;
            transform: translate(-50%, -50%) scale(0.8);
        }
        50% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1.05);
        }
        55% {
            transform: translate(-50%, -50%) scale(1);
        }
        100% {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1);
        }
    }
    
    @keyframes buttonFadeIn {
        0% {
            opacity: 0;
        }
        60% {
            opacity: 0;
        }
        100% {
            opacity: 1;
        }
    }
    
    .sports-ball {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 100px;
        z-index: 9998;
        animation: ballBounce 3s ease-out forwards;
        opacity: 0;
    }
    
    .football-ball {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 100px;
        z-index: 9997;
        animation: footballBounce 3s ease-out forwards;
        opacity: 0;
    }
    
    .basketball-ball {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 100px;
        z-index: 9996;
        animation: basketballBounce 3s ease-out forwards;
        opacity: 0;
    }
    
    .stadium-lights {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: 9999;
        animation: stadiumLights 3s ease-out forwards;
        pointer-events: none;
    }
    
    .action-lines {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 400px;
        height: 4px;
        background: linear-gradient(90deg, transparent 0%, rgba(139, 92, 246, 0.8) 50%, transparent 100%);
        z-index: 9997;
        animation: actionLines 3s ease-out forwards;
        opacity: 0;
    }
    
    .action-lines::before,
    .action-lines::after {
        content: '';
        position: absolute;
        width: 300px;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, rgba(139, 92, 246, 0.6) 50%, transparent 100%);
    }
    
    .action-lines::before {
        top: -30px;
        left: 50px;
    }
    
    .action-lines::after {
        bottom: -30px;
        right: 50px;
    }
    
    .arena-vision-logo {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 120px;
        font-weight: 900;
        text-align: center;
        z-index: 10000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        letter-spacing: 8px;
        animation: logoFadeIn 3s ease-out forwards;
        opacity: 0;
    }
    
    .arena-text {
        color: #8B5CF6;
        text-shadow: 0 0 30px rgba(139, 92, 246, 0.8), 0 0 60px rgba(139, 92, 246, 0.5);
    }
    
    .vision-text {
        color: #FFFFFF;
        text-shadow: 0 0 30px rgba(255, 255, 255, 0.5), 0 0 60px rgba(255, 255, 255, 0.3);
    }
    
    .landing-container {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: #000000;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .begin-button-wrapper {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, 0%);
        margin-top: 180px;
        z-index: 10001;
        opacity: 0;
        animation: buttonFadeIn 3s ease-out forwards;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # HTML for sports animation and logo with clickable overlay
    st.markdown("""
    <div class="landing-container" id="landing-container" style="cursor: pointer;">
        <div class="action-lines"></div>
        <div class="sports-ball">⚽</div>
        <div class="football-ball">🏈</div>
        <div class="basketball-ball">🏀</div>
        <div class="stadium-lights"></div>
        <div class="arena-vision-logo"><span class="arena-text">ARENA</span><span class="vision-text">VISION</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Style for the Begin button
    st.markdown("""
    <style>
    /* Hide sidebar and header buttons */
    [data-testid="stSidebar"] button,
    header button {
        display: none !important;
    }
    
    .begin-button-container {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        z-index: 10001 !important;
        opacity: 0;
        animation: buttonFadeIn 3s ease-out forwards;
        text-align: center !important;
        width: auto !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    /* Center Streamlit button wrapper - remove any background/border */
    .begin-button-container > div,
    .begin-button-container [data-testid="baseButton-secondary"],
    .begin-button-container [data-testid="stButton"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin: 0 auto !important;
        width: auto !important;
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }
    
    .begin-button-container button,
    button[key="begin_button"] {
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 36px !important;
        font-weight: 600 !important;
        padding: 12px 40px !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
        letter-spacing: 4px !important;
        text-shadow: 0 0 20px rgba(255, 255, 255, 0.5), 0 0 40px rgba(255, 255, 255, 0.3) !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        box-shadow: none !important;
        display: block !important;
        margin: 0 auto !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: relative !important;
        left: auto !important;
        right: auto !important;
    }
    
    .begin-button-container button:hover,
    button[key="begin_button"]:hover {
        transform: scale(1.05) !important;
        text-shadow: 0 0 30px rgba(255, 255, 255, 0.7), 0 0 60px rgba(255, 255, 255, 0.5) !important;
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    
    .begin-button-container button:active,
    button[key="begin_button"]:active {
        transform: scale(0.98) !important;
        color: #FFFFFF !important;
    }
    </style>
    <div class="begin-button-container">
    """, unsafe_allow_html=True)
    
    # Check if we should navigate (from query param or button click)
    query_params = st.query_params
    if query_params.get("begin") == "true":
        st.session_state.show_landing = False
        st.query_params.clear()
        st.rerun()
    
    # Begin button
    if st.button("Begin", key="begin_button", use_container_width=False):
        st.session_state.show_landing = False
        st.rerun()
    
    # Add JavaScript to make entire page clickable
    st.markdown("""
    <script>
    (function() {
        function setupClickHandler() {
            const landingContainer = document.getElementById('landing-container');
            if (landingContainer) {
                landingContainer.style.cursor = 'pointer';
                landingContainer.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    // Navigate with query parameter
                    const currentUrl = window.location.href;
                    const separator = currentUrl.includes('?') ? '&' : '?';
                    window.location.href = currentUrl + separator + 'begin=true';
                });
            }
        }
        
        // Wait for DOM to be ready
        function init() {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(setupClickHandler, 300);
                });
            } else {
                setTimeout(setupClickHandler, 300);
            }
        }
        
        init();
        // Retry after Streamlit renders
        setTimeout(setupClickHandler, 1000);
    })();
    </script>
    """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def main():
    """Main Streamlit app."""
    # Show landing page first
    if st.session_state.show_landing:
        show_landing_page()
        return
    
    # Check if we should show the next/final page
    if st.session_state.get("current_page") == "next_page":
        show_next_page()
        return
    if st.session_state.get("current_page") == "final":
        show_final_page()
        return
    
    # Add modern styling and animations
    st.markdown("""
    <style>
    /* Modern Sports Theme Styling */
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Bebas+Neue&family=Montserrat:wght@400;500;600;700;800&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    
    /* Animated background particles */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 20% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(255, 100, 0, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 40% 20%, rgba(0, 255, 150, 0.05) 0%, transparent 50%);
        animation: particleFloat 20s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes particleFloat {
        0%, 100% { transform: translate(0, 0) scale(1); }
        50% { transform: translate(20px, -20px) scale(1.1); }
    }
    
    /* Title Styling */
    h1 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 3rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    
    h1 .arena-text {
        color: #8B5CF6 !important;
        background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.5));
    }
    
    h1 .vision-text {
        color: #ffffff !important;
        background: linear-gradient(135deg, #ffffff 0%, #a0a0a0 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.3));
    }
    
    @keyframes titleGlow {
        0%, 100% { filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.5)); }
        50% { filter: drop-shadow(0 0 20px rgba(139, 92, 246, 0.7)); }
    }
    
    h1 .arena-text {
        animation: titleGlow 3s ease-in-out infinite;
    }
    
    /* Subtitle */
    .main-subtitle {
        font-size: 1.1rem;
        color: #b0b0b0;
        font-weight: 400;
        margin-bottom: 2rem;
        letter-spacing: 0.01em;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0f0f 0%, #1a1a2e 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    [data-testid="stSidebar"] .stMarkdown h2 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
        padding-bottom: 0.5rem;
        padding-left: 2rem !important;
        position: relative;
        border-bottom: 2px solid rgba(139, 92, 246, 0.3);
    }
    
    [data-testid="stSidebar"] .stMarkdown h2::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(180deg, #8B5CF6 0%, #A78BFA 100%);
        border-radius: 2px;
    }
    
    /* Radio buttons with hover effect */
    [data-testid="stSidebar"] label {
        transition: all 0.3s ease;
        border-radius: 8px;
        padding: 0.5rem;
    }
    
    [data-testid="stSidebar"] label:hover {
        background: rgba(139, 92, 246, 0.1);
        transform: translateX(5px);
    }
    
    /* Checkbox styling */
    [data-testid="stSidebar"] .stCheckbox label {
        color: #e0e0e0;
        font-weight: 500;
    }
    
    /* Header Styling */
    h2 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
        position: relative;
        padding-left: 2.5rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    
    h2::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(180deg, #8B5CF6 0%, #A78BFA 100%);
        border-radius: 2px;
    }
    
    /* Subheader */
    h3 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        color: #d0d0d0 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    
    /* File Uploader - reduced height */
    [data-testid="stFileUploader"] > div {
        min-height: 80px !important;
        height: 80px !important;
    }
    
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
        min-height: 80px !important;
        height: 80px !important;
    }
    
    /* Input Fields - match file uploader height exactly */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        padding: 0.75rem 1rem !important;
        transition: all 0.3s ease !important;
        min-height: 80px !important;
        height: 80px !important;
    }
    
    /* Make text input container match file uploader height */
    .stTextInput > div {
        min-height: 80px !important;
        height: 80px !important;
    }
    
    .stTextInput > div > div {
        min-height: 80px !important;
        height: 80px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    .stTextInput > div > div > input:focus {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: #8B5CF6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
        outline: none !important;
    }
    
    /* File Uploader */
    .uploadedFile {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 2px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        transition: all 0.3s ease !important;
    }
    
    .uploadedFile:hover {
        border-color: #8B5CF6 !important;
        background: rgba(139, 92, 246, 0.05) !important;
        transform: translateY(-2px);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
        position: relative;
        overflow: hidden;
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
    }
    
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Slider */
    .stSlider {
        margin: 1rem 0;
    }
    
    .stSlider > div > div {
        background: rgba(255, 255, 255, 0.1) !important;
    }
    
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #8B5CF6 0%, #A78BFA 100%) !important;
    }
    
    /* Info boxes */
    .stInfo {
        background: rgba(139, 92, 246, 0.1) !important;
        border-left: 4px solid #8B5CF6 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }
    
    /* Columns with animation */
    [data-testid="column"] {
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Progress bar styling */
    .stProgress {
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }
    
    .stProgress > div {
        background: #6D28D9 !important;
        border-radius: 10px !important;
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stProgress > div > div {
        background: #6D28D9 !important;
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    .stProgress > div > div > div {
        background: #A78BFA !important;
        background-size: 200% 100% !important;
        animation: progressShimmer 2s linear infinite !important;
        border: none !important;
    }
    
    @keyframes progressShimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    /* Hide Streamlit default elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)
    
    _sidebar_brand_logo()
    
    # Modern title with ARENA in purple
    st.markdown('<h1><span class="arena-text">ARENA</span><span class="vision-text">VISION</span></h1>', unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Intelligent sports highlight generation with agentic AI</p>', unsafe_allow_html=True)
    
    # Sidebar for mode selection
    st.sidebar.header("Input Mode")
    input_mode = st.sidebar.radio(
        "Select input source:",
        ["YouTube / Upload", "Live Stream"],
        help="Choose how to provide video input"
    )
    
    # Fast mode option
    st.sidebar.header("Processing Options")
    fast_mode = st.sidebar.checkbox(
        "Fast Mode (Skip Video Intelligence API)",
        value=False,
        help="Faster processing for short videos. Uses only Gemini Vision analysis."
    )
    
    # Main content area
    if input_mode == "YouTube / Upload":
        youtube_upload_mode(fast_mode)
    else:
        live_stream_mode()
    
    # Display results if available
    if st.session_state.results and st.session_state.results.get("status") == "complete":
        display_results(st.session_state.results)


def youtube_upload_mode(fast_mode: bool = False):
    """YouTube/Upload input mode."""
    st.header("Video Input")
    
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
    st.header("Live Stream Input")
    
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
    st.info("**Tip**: For demo purposes, you can use a prerecorded video and process it frame-by-frame to simulate live mode.")


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
            status_text.text(f"Complete! (Took {elapsed:.1f} seconds)")
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
                    st.info("**Tip**: Try using the **Upload Video** option on the right for more reliable processing")
            elif results.get("status") == "no_highlights":
                st.warning("No highlights detected")
                st.info(results.get("message", "No highlight-worthy moments found. Try a different video or enable more detection features."))
                st.info("**Tips**: Try disabling Fast Mode to use Video Intelligence API, or use a video with more clear scoring plays.")
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
    
    st.header("Results")
    
    summary = results.get("summary", {})
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Highlights Found", summary.get("highlights_found", 0))
    with col2:
        st.metric("Total Duration", f"{summary.get('total_duration', 0):.1f}s")
    with col3:
        st.metric("Status", "Complete")
    
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
        st.subheader("Highlight Reel Editor")
        
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
                st.subheader("Continue")
                if st.button("Continue", type="primary", key="continue_button"):
                    st.session_state.current_page = "next_page"
                    st.rerun()
    
    with col_chat:
        st.subheader("Video Editing Chatbot")
        
        # Show video context info
        with st.expander("Video Context", expanded=False):
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
                    st.write(f"**You:** {content}...")
                else:
                    st.write(f"**Bot:** {content}...")
        
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
        st.subheader("Individual Video Segments")
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
                                    label=f"Download Segment {clip_idx + 1}",
                                    data=f.read(),
                                    file_name=clip_name,
                                    mime="video/mp4",
                                    key=f"download_segment_{clip_idx}"
                                )
                        else:
                            st.warning(f"Clip {clip_idx + 1} not found")
    

def show_next_page():
    """Show the logo generation page with WHISK/Imagen."""
    # Apply the same modern styling as main page
    st.markdown("""
    <style>
    /* Modern Sports Theme Styling */
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Bebas+Neue&family=Montserrat:wght@400;500;600;700;800&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    
    /* Animated background particles */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 20% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(255, 100, 0, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 40% 20%, rgba(0, 255, 150, 0.05) 0%, transparent 50%);
        animation: particleFloat 20s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes particleFloat {
        0%, 100% { transform: translate(0, 0) scale(1); }
        50% { transform: translate(20px, -20px) scale(1.1); }
    }
    
    /* Title Styling */
    h1 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 3rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #ffffff !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Header Styling */
    h2 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
        position: relative;
        padding-left: 2.5rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        animation: fadeInUp 0.6s ease-out 0.2s both;
    }
    
    h2::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(180deg, #8B5CF6 0%, #A78BFA 100%);
        border-radius: 2px;
    }
    
    /* Subheader */
    h3 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 1.3rem !important;
        font-weight: 500 !important;
        color: #d0d0d0 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 0.75rem !important;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        padding: 1.5rem 1rem !important;
        min-height: 60px !important;
        height: 60px !important;
        transition: all 0.3s ease !important;
        font-family: 'Montserrat', sans-serif !important;
        font-size: 1rem !important;
    }
    
    .stTextInput > div {
        min-height: 60px !important;
    }
    
    .stTextInput > div > div {
        min-height: 60px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    .stTextInput > div > div > input:focus {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: #8B5CF6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
        outline: none !important;
    }
    
    /* File Uploader */
    [data-testid="stFileUploader"] > div {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 2px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stFileUploader"] > div:hover {
        border-color: #8B5CF6 !important;
        background: rgba(139, 92, 246, 0.05) !important;
        transform: translateY(-2px);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        font-family: 'Montserrat', sans-serif !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
        position: relative;
        overflow: hidden;
        max-width: 300px !important;
        width: auto !important;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
    }
    
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Secondary buttons */
    [data-testid="baseButton-secondary"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    
    [data-testid="baseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: #8B5CF6 !important;
    }
    
    /* Columns with animation */
    [data-testid="column"] {
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #b0b0b0 !important;
        font-family: 'Montserrat', sans-serif !important;
        animation: fadeInUp 0.6s ease-out 0.1s both;
    }
    
    /* Images */
    .stImage {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        transition: transform 0.3s ease !important;
        animation: fadeInUp 0.6s ease-out 0.3s both;
    }
    
    .stImage:hover {
        transform: scale(1.02);
    }
    
    /* Video player */
    video {
        border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        animation: fadeInUp 0.6s ease-out 0.3s both;
    }
    
    /* Divider */
    hr {
        border-color: rgba(139, 92, 246, 0.3) !important;
        margin: 2rem 0 !important;
    }
    
    /* Success/Info messages */
    .stSuccess, .stInfo {
        background: rgba(139, 92, 246, 0.1) !important;
        border-left: 4px solid #8B5CF6 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Warning messages */
    .stWarning {
        background: rgba(255, 193, 7, 0.1) !important;
        border-left: 4px solid #ffc107 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Error messages */
    .stError {
        background: rgba(244, 67, 54, 0.1) !important;
        border-left: 4px solid #f44336 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Expander */
    [data-testid="stExpander"] {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        margin: 1rem 0 !important;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Logo Generation")
    st.markdown("Generate a logo using Google's WHISK (Imagen) image generation or upload your own logo.")
    
    # Initialize session state for image generation
    if "generated_images" not in st.session_state:
        st.session_state.generated_images = []
    if "selected_image" not in st.session_state:
        st.session_state.selected_image = None
    if "logo_prompt" not in st.session_state:
        st.session_state.logo_prompt = ""
    
    # Prompt input
    st.subheader("Describe Your Logo")
    prompt = st.text_input(
        "Enter a description of the logo you want to generate:",
        value=st.session_state.logo_prompt,
        placeholder="e.g., 'A modern basketball logo with a basketball and lightning bolt, blue and orange colors, minimalist design'",
        key="logo_prompt_input"
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        generate_button = st.button("Generate Logo", type="primary")
    
    with col2:
        if st.button("Reprompt"):
            st.session_state.generated_images = []
            st.session_state.selected_image = None
            st.rerun()

    # Upload a logo instead of generating
    st.subheader("Upload a Logo")
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
        st.success("Logo uploaded and selected")
    
    # Generate images
    if generate_button and prompt:
        st.session_state.logo_prompt = prompt
        with st.spinner("Generating logo variations... This may take a moment."):
            from utils.image_generator import generate_logo_images
            generated = generate_logo_images(prompt, num_images=3)
            st.session_state.generated_images = generated
    
    # Display generated images
    if st.session_state.generated_images:
        st.subheader("Generated Logo Options")
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
                                st.toast(f"Selected Option {idx + 1}!")
                                st.rerun()
                        else:
                            st.warning(f"Image {idx + 1} not found")
                    else:
                        st.warning(f"Option {idx + 1} generation failed")
        else:
            st.error("No images were generated. Please try a different prompt or check your API configuration.")
            
            # Show helpful error information
            with st.expander("Troubleshooting"):
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
                    st.error("`GOOGLE_CLOUD_PROJECT` is not set in your `.env` file")
    
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
                        label="Download Selected Logo",
                        data=f.read(),
                        file_name=f"logo_{hash(st.session_state.logo_prompt) % 10000}.png",
                        mime="image/png",
                        key="download_logo",
                        use_container_width=True
                    )
    
    # Skip only the logo step (continue to intro generation)
    st.divider()
    col_text, col_button = st.columns([2, 1])
    with col_text:
        st.markdown('<p style="font-family: \'Oswald\', sans-serif; color: #FFFFFF; font-size: 1.6rem; margin: 0; padding-top: 0.5rem; font-weight: 600;">Don\'t want to upload a logo?</p>', unsafe_allow_html=True)
    with col_button:
        if st.button("Skip Logo", key="skip_logo"):
            st.session_state.skip_logo = True
            st.toast("Skipped logo step")
            st.rerun()

    # Veo Intro Video Generation Section
    st.divider()
    st.subheader("Intro Video Generation")
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
        st.write("**Text to Display**")
        intro_text = st.text_input(
            "Enter text to display on video (centered):",
            value=st.session_state.intro_text or video_summary or "Game Highlights",
            placeholder="e.g., 'Game Highlights' or 'Top Plays'",
            key="intro_text_input",
            help="This text will be centered on the video"
        )
    
    with col_bg:
        st.write("**Background Description**")
        intro_background = st.text_input(
            "Describe the background style:",
            value=st.session_state.intro_background or "dark blue gradient with animated particles",
            placeholder="e.g., 'dark blue gradient', 'bright energetic', 'red fire theme'",
            key="intro_background_input",
            help="Describe the visual style of the background (colors, theme, effects)"
        )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        generate_video_button = st.button("Generate Intro Video", type="primary")
    
    with col2:
        if st.button("Regenerate"):
            st.session_state.intro_videos = []
            st.session_state.selected_intro_video = None
            st.rerun()
    
    # Generate intro videos
    if generate_video_button and intro_text and intro_background:
        st.session_state.intro_text = intro_text
        st.session_state.intro_background = intro_background
        with st.spinner("Generating intro video with Veo 3.0... This may take a few minutes."):
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
        st.subheader("Generated Intro Video Options")
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
                                st.toast(f"Selected Intro Video {idx + 1}!")
                                st.rerun()
                        else:
                            st.warning(f"Video {idx + 1} not found")
                    else:
                        st.warning(f"Option {idx + 1} generation failed")
        else:
            st.error("No intro videos were generated. Please try again or check your API configuration.")
    
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
                        label="Download Selected Intro Video",
                        data=f.read(),
                        file_name=f"intro_{hash(st.session_state.intro_prompt) % 10000}.mp4",
                        mime="video/mp4",
                        key="download_intro_video",
                        use_container_width=True
                    )
    
    # Continue button (logo optional; allow continue if intro video selected)
    if st.session_state.selected_intro_video:
        st.divider()
        if st.button("Continue", type="primary"):
            # Navigate to final page
            st.session_state.current_page = "final"
            st.rerun()

    # Skip intro button: allow users to go straight to final/download/twitter page
    st.divider()
    col_text_intro, col_button_intro = st.columns([2, 1])
    with col_text_intro:
        st.markdown('<p style="font-family: \'Oswald\', sans-serif; color: #FFFFFF; font-size: 1.6rem; margin: 0; padding-top: 0.5rem; font-weight: 600;">Don\'t want to add an intro?</p>', unsafe_allow_html=True)
    with col_button_intro:
        if st.button("Skip Intro and Go to Final", key="skip_intro_and_final"):
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
    # Apply the same modern styling as other pages
    st.markdown("""
    <style>
    /* Modern Sports Theme Styling */
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;500;600;700&family=Bebas+Neue&family=Montserrat:wght@400;500;600;700;800&display=swap');
    
    /* Global Styles */
    .stApp {
        font-family: 'Montserrat', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
    }
    
    /* Animated background particles */
    .stApp::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: 
            radial-gradient(circle at 20% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 80% 80%, rgba(255, 100, 0, 0.1) 0%, transparent 50%),
            radial-gradient(circle at 40% 20%, rgba(0, 255, 150, 0.05) 0%, transparent 50%);
        animation: particleFloat 20s ease-in-out infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes particleFloat {
        0%, 100% { transform: translate(0, 0) scale(1); }
        50% { transform: translate(20px, -20px) scale(1.1); }
    }
    
    /* Title Styling */
    h1 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 3rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #ffffff !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Header Styling */
    h2 {
        font-family: 'Oswald', sans-serif !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #ffffff !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
        position: relative;
        padding-left: 2.5rem !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        animation: fadeInUp 0.6s ease-out 0.2s both;
    }
    
    h2::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        width: 4px;
        background: linear-gradient(180deg, #8B5CF6 0%, #A78BFA 100%);
        border-radius: 2px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        font-family: 'Montserrat', sans-serif !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
        position: relative;
        overflow: hidden;
        max-width: 300px !important;
        width: auto !important;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
    }
    
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    
    /* Secondary buttons */
    [data-testid="baseButton-secondary"] {
        background: rgba(255, 255, 255, 0.1) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }
    
    [data-testid="baseButton-secondary"]:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        border-color: #8B5CF6 !important;
    }
    
    /* Download button */
    [data-testid="stDownloadButton"] > button {
        background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.75rem 2rem !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        font-family: 'Montserrat', sans-serif !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
        animation: fadeInUp 0.6s ease-out 0.3s both;
    }
    
    [data-testid="stDownloadButton"] > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
    }
    
    /* Video player */
    video {
        border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
        animation: fadeInUp 0.6s ease-out 0.3s both;
    }
    
    /* Text area */
    .stTextArea > div > div > textarea {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #ffffff !important;
        padding: 1rem !important;
        font-family: 'Montserrat', sans-serif !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: #8B5CF6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
        outline: none !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #b0b0b0 !important;
        font-family: 'Montserrat', sans-serif !important;
        animation: fadeInUp 0.6s ease-out 0.1s both;
    }
    
    /* Success/Info messages */
    .stSuccess, .stInfo {
        background: rgba(139, 92, 246, 0.1) !important;
        border-left: 4px solid #8B5CF6 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Error messages */
    .stError {
        background: rgba(244, 67, 54, 0.1) !important;
        border-left: 4px solid #f44336 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Warning messages */
    .stWarning {
        background: rgba(255, 193, 7, 0.1) !important;
        border-left: 4px solid #ffc107 !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Divider */
    hr {
        border-color: rgba(139, 92, 246, 0.3) !important;
        margin: 2rem 0 !important;
    }
    
    /* Columns with animation */
    [data-testid="column"] {
        animation: fadeInUp 0.6s ease-out;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("Final Video")
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

    st.subheader("Final Video")
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
            label="Download Final Video",
            data=video_bytes,
            file_name=video_path.name,
            mime="video/mp4",
            key="download_final_video"
        )

    st.markdown("---")

    st.subheader("Post to X (Twitter)")
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
                 st.success("Posted to X successfully!")
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
                         st.success("Posted to X successfully!")
                    else:
                        st.error(f"Failed to post tweet (v2): {resp3.status_code} {resp3.text}")

        except Exception as e:
            st.error(f"Error posting to X: {e}")


if __name__ == "__main__":
    main()
