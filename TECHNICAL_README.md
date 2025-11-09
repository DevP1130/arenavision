# 🎥 ArenaVision - Technical Documentation

## Overview

ArenaVision is an intelligent sports highlight generation system built with an **agentic AI architecture**. It automatically analyzes sports videos, detects key moments, creates highlight reels, and generates commentary using Google Cloud's AI services.

---

## 🏗️ Architecture: Agent-Based System

The system uses a **multi-agent pipeline architecture** where specialized agents process video through sequential stages:

```
┌─────────────┐
│ Input Agent │ → Handles video input (YouTube/Upload/Live Stream)
└─────────────┘
      ↓
┌─────────────┐
│Vision Agent │ → Analyzes video content (detects plays, events)
└─────────────┘
      ↓
┌─────────────┐
│Planner Agent│ → Ranks moments, creates highlight segments
└─────────────┘
      ↓
┌─────────────┐
│Editor Agent │ → Extracts & compiles highlight reel
└─────────────┘
      ↓
┌──────────────┐
│Commentator   │ → Generates text & audio commentary
│Agent         │
└──────────────┘
```

### Key Design Principles:
- **Modularity**: Each agent has a single responsibility
- **Extensibility**: Easy to add new agents or modify existing ones
- **Error Handling**: Each agent handles errors gracefully with fallbacks
- **State Management**: Pipeline orchestrator manages data flow between agents

---

## 🛠️ Technical Stack

### Core Technologies:
- **Python 3.9+**: Main programming language
- **Streamlit**: Web UI framework for interactive frontend
- **MoviePy**: Video editing and manipulation
- **yt-dlp**: YouTube video downloading
- **OpenCV**: Video processing utilities

### Google Cloud Services:
- **Video Intelligence API**: Detects sports events, shot changes, objects
- **Gemini 2.0 Flash**: Vision analysis and text generation
- **Veo 3.1**: Video generation (intro videos)
- **Imagen 3 (WHISK)**: Logo/image generation
- **Text-to-Speech (gTTS)**: Audio commentary generation

### Key Libraries:
- `google-cloud-videointelligence`: Video analysis
- `google-generativeai`: Gemini API access
- `google-cloud-aiplatform`: Vertex AI services
- `pydub`: Audio processing
- `pillow`: Image processing

---

## 📊 Pipeline Flow (Step-by-Step)

### Step 1: Input Agent (`agents/input_agent.py`)

**Purpose**: Handle video input from multiple sources

**Process**:
1. Detects input type (YouTube URL, file path, or stream URL)
2. **YouTube Mode**: Downloads video using `yt-dlp` with custom headers
3. **Upload Mode**: Validates and returns file path
4. **Live Stream Mode**: Sets up RTSP connection

**Output**:
```python
{
    "video_path": "/path/to/video.mp4",
    "mode": "youtube" | "upload" | "live",
    "status": "ready"
}
```

**Technical Details**:
- Uses `YouTubeHandler` class for YouTube downloads
- Handles 403 errors with custom user agents
- Automatically converts to MP4 format

---

### Step 2: Vision Agent (`agents/vision_agent.py`)

**Purpose**: Analyze video content to detect plays, events, and key moments

**Dual Analysis Approach**:

#### A. Video Intelligence API
- **Label Detection**: Identifies sports events (goals, baskets, touchdowns)
- **Shot Change Detection**: Finds scene transitions
- **Object Tracking**: Tracks moving objects (optional, for longer videos)
- **Fast Mode**: For videos < 3 minutes, uses fewer features

#### B. Gemini Vision Analysis
- Samples key frames throughout the video (10-40 frames based on duration)
- Analyzes each frame for:
  - Event detection (plays, scoring moments)
  - Success detection (made/missed shots)
  - Player visibility
  - Crowd reaction (0-10 excitement scale)
  - Highlight-worthiness

**Output**:
```python
{
    "detections": {
        "key_frames": [...],  # Shot changes
        "events": [...],      # Detected events from Gemini
        "plays": [...]        # Sports events from Video Intelligence
    },
    "metadata": {
        "video_path": "...",
        "analysis_complete": True
    }
}
```

**Technical Details**:
- Frame sampling uses `utils.video_utils.sample_key_frames()`
- Gemini Vision uses `gemini-2.0-flash-exp` model
- Handles rate limiting (10 requests/minute for experimental models)

---

### Step 3: Planner Agent (`agents/planner_agent.py`)

**Purpose**: Create structured highlight plan by ranking moments and organizing segments

**Process**:

1. **Moment Collection**: Gathers all potential highlights from:
   - Gemini Vision events
   - Video Intelligence plays
   - Shot changes
   - Timeline-based segments (fallback)

2. **Ranking System**: Scores each moment using:
   - Base confidence from detection
   - Success bonus (+0.5 for successful plays)
   - Ending bonus (+0.4 for last 30 seconds)
   - Action bonus (+0.2 for detected action)
   - Crowd reaction (+0.1 to +0.3)
   - Random variation (±0.05) for diversity

3. **Segment Creation**: Creates video segments with:
   - **Pre-buffers**: 2 seconds (regular) or 5-7 seconds (scoring plays)
   - **Post-buffers**: 5 seconds
   - **Duration limits**: 3-30 seconds
   - **Overlap detection**: Removes segments within 3 seconds

4. **Fallback Mechanisms**: If no ranked moments found:
   - Uses top events from Gemini Vision
   - Uses top shot changes
   - Creates timeline-based segments
   - Default segment from video start

5. **Ending Guarantee**: Always includes last 15 seconds if not covered

**Output**:
```python
{
    "plan": {
        "segments": [
            {
                "start": 12.5,
                "end": 25.0,
                "duration": 12.5,
                "description": "Successful goal",
                "score": 0.85
            },
            ...
        ],
        "total_duration": 120.5,
        "highlight_count": 8
    }
}
```

---

### Step 4: Editor Agent (`agents/editor_agent.py`)

**Purpose**: Extract video segments and compile into final highlight reel

**Process**:

1. **Segment Extraction**:
   - Uses MoviePy's `VideoFileClip.subclipped()` method
   - Extracts each segment from original video
   - Saves individual segment files (`segment_000.mp4`, etc.)
   - Handles edge cases (segments exceeding video duration)

2. **Veo Editing (Optional)**:
   - Can enhance clips using Google Veo 3.1
   - Applies cinematic effects, slow-motion, stabilization
   - Currently placeholder (API integration pending)

3. **Reel Compilation**:
   - Compiles all segments into single highlight reel
   - Adds smooth crossfade transitions (0.5 seconds)
   - Uses opacity blending for fade effects:
     - First clip: fades out at end
     - Last clip: fades in at start
     - Middle clips: fade in AND fade out
   - Exports as MP4 using MoviePy

**Output**:
```python
{
    "highlight_reel": "/path/to/highlight_reel.mp4",
    "clips": ["/path/to/segment_000.mp4", ...],
    "segment_count": 8,
    "status": "complete"
}
```

**Technical Details**:
- Uses `CompositeVideoClip` for overlaying clips with transitions
- Frame-level opacity manipulation for smooth fades
- Handles missing segments gracefully

---

### Step 5: Commentator Agent (`agents/commentator_agent.py`)

**Purpose**: Generate text and audio commentary for highlight segments

**Process**:

1. **Segment Commentary**:
   - Generates 1-2 sentences per segment using Gemini
   - Matches energy level to importance score
   - Includes segment position in reel

2. **Overall Narration**:
   - Creates introduction for highlight reel
   - Mentions highlight count and duration

3. **Text-to-Speech**:
   - Converts commentary to audio using Google Text-to-Speech (gTTS)
   - Combines narration and segment commentaries
   - Exports as MP3 file

**Output**:
```python
{
    "commentaries": [
        {
            "segment_index": 0,
            "text": "Amazing goal in the first highlight!",
            "timestamp": 12.5,
            "duration": 12.5
        },
        ...
    ],
    "overall_narration": "Welcome to the highlights...",
    "audio_file": "/path/to/commentary.mp3"
}
```

**Technical Details**:
- Uses `gemini-2.0-flash-exp` model (rate limit: 10 req/min)
- Falls back to generic commentary on errors
- Combines audio using `pydub`

---

## 🔧 Key Technical Components

### Pipeline Orchestrator (`pipeline.py`)

**Class**: `GameWatcherPipeline`

**Responsibilities**:
- Initializes all agents
- Manages data flow between agents
- Handles progress callbacks
- Error handling and fallbacks
- Combines results from all agents

**Key Method**:
```python
def process(input_source: str, mode: str = "auto", progress_callback=None) -> Dict
```

**Progress Tracking**:
- 10%: Input processing
- 20-50%: Vision analysis
- 55-65%: Planning
- 70-85%: Editing
- 90-95%: Commentary
- 100%: Complete

---

### Frontend (`app.py`)

**Framework**: Streamlit

**Key Features**:
- **Landing Page**: Animated sports-themed welcome screen
- **Main Page**: Video input (YouTube/Upload/Live Stream)
- **Results Page**: Displays highlight reel, segments, commentary
- **Editor Page**: Iterative video editing with chatbot
- **Logo/Intro Page**: Logo generation (Imagen) and intro video (Veo)
- **Final Page**: Download and post to X (Twitter)

**Session State Management**:
- `pipeline`: GameWatcherPipeline instance
- `results`: Processing results
- `iterations`: List of edited video iterations
- `current_page`: Navigation state
- `chat_history`: Chatbot conversation

**UI Styling**:
- Modern sports theme with purple gradient
- Oswald font for headings, Montserrat for body
- Animated background particles
- Smooth transitions and hover effects

---

### Handlers

#### YouTube Handler (`handlers/youtube_handler.py`)
- Downloads videos using `yt-dlp`
- Handles 403 errors with custom headers
- Converts to MP4 format

#### Live Stream Handler (`handlers/live_stream_handler.py`)
- Connects to RTSP streams
- Processes in chunks (10-second segments)
- Handles real-time video capture

---

### Utilities

#### Video Utils (`utils/video_utils.py`)
- `sample_key_frames()`: Evenly samples frames throughout video
- `get_video_info()`: Extracts video metadata
- `overlay_logo_on_video()`: Adds logo watermark

#### Video Editor (`utils/video_editor.py`)
- `apply_editing_instructions()`: Processes chatbot editing requests
- Handles segment removal, trimming, reordering

#### Image Generator (`utils/image_generator.py`)
- Generates logos using Imagen 3 (WHISK)
- Creates 3 variations per prompt

#### Veo Generator (`utils/veo_generator.py`)
- Generates intro videos using Veo 3.1
- Creates 3 variations with different styles

---

## 🔌 API Integrations

### Google Video Intelligence API

**Endpoint**: `v1/videos:annotate`

**Features Used**:
- `LABEL_DETECTION`: Detects sports events
- `SHOT_CHANGE_DETECTION`: Finds scene transitions
- `OBJECT_TRACKING`: Tracks moving objects (optional)

**Configuration**:
```python
features = [
    videointelligence.Feature.LABEL_DETECTION,
    videointelligence.Feature.SHOT_CHANGE_DETECTION
]
```

**Rate Limits**: Standard API quotas apply

---

### Gemini API

**Models Used**:
- `gemini-2.0-flash-exp`: Vision analysis and text generation
- `gemini-1.5-flash`: Fallback for higher quotas

**Endpoints**:
- Vision: `generateContent()` with image inputs
- Text: `generateContent()` with text prompts

**Rate Limits**:
- Experimental models: 10 requests/minute
- Preview models: Higher quotas

---

### Veo 3.1 API

**Purpose**: Generate intro videos

**Process**:
1. Creates video generation request
2. Polls for completion
3. Downloads generated video

**Status**: Placeholder implementation (API integration pending)

---

### Imagen 3 (WHISK) API

**Purpose**: Generate logos

**Process**:
1. Sends prompt to Vertex AI
2. Generates 3 image variations
3. Returns image paths

**Configuration**:
- Model: `imagegeneration@006`
- Image size: 1024x1024
- Number of images: 3

---

## 🚀 Setup & Configuration

### 1. Environment Variables (`.env`)

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GOOGLE_API_KEY=your-api-key

# Twitter (optional, for posting)
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...
```

### 2. Service Account Setup

1. Create service account in Google Cloud Console
2. Grant roles:
   - Vertex AI User
   - Video Intelligence API User
3. Download JSON key file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` path

### 3. Enable APIs

Enable in Google Cloud Console:
- Video Intelligence API
- Vertex AI API
- Generative AI API

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

**Key Dependencies**:
- `streamlit>=1.28.0`
- `google-cloud-videointelligence>=2.17.0`
- `google-generativeai>=0.3.0`
- `moviepy>=1.0.3,<2.0`
- `decorator>=4.4.1,<4.4.2` (compatibility with MoviePy)
- `yt-dlp>=2023.10.7`
- `gtts>=2.4.0`

### 5. Run Application

```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
hack/
├── agents/              # Agent implementations
│   ├── base_agent.py   # Abstract base class
│   ├── input_agent.py  # Video input handling
│   ├── vision_agent.py # Video analysis
│   ├── planner_agent.py # Highlight planning
│   ├── editor_agent.py # Video editing
│   ├── commentator_agent.py # Commentary generation
│   └── chatbot_agent.py # Interactive editing
├── handlers/           # Input handlers
│   ├── youtube_handler.py
│   └── live_stream_handler.py
├── utils/              # Utility functions
│   ├── video_utils.py
│   ├── video_editor.py
│   ├── image_generator.py
│   └── veo_generator.py
├── app.py              # Streamlit frontend
├── pipeline.py         # Pipeline orchestrator
├── config.py           # Configuration management
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (not in repo)
```

---

## 🔄 Data Flow Example

**Input**: YouTube URL → `https://youtube.com/watch?v=...`

1. **Input Agent** downloads video → `uploads/youtube_video.mp4`
2. **Vision Agent** analyzes → Detects 15 events, 8 shot changes
3. **Planner Agent** ranks → Selects top 8 highlights, creates segments
4. **Editor Agent** extracts → Creates `highlight_reel.mp4` with 8 segments
5. **Commentator Agent** generates → Creates `commentary.mp3` with 8 commentaries

**Output**: 
- Highlight reel video
- Individual segment clips
- Commentary audio file
- Metadata (timestamps, descriptions, scores)

---

## 🎯 Key Technical Decisions

1. **Agent Architecture**: Modular design allows easy extension and testing
2. **Dual Vision Analysis**: Combines Video Intelligence (structured) + Gemini Vision (contextual)
3. **Fallback Mechanisms**: Multiple fallbacks ensure system works even with limited detections
4. **MoviePy for Editing**: Reliable, well-documented video editing library
5. **Streamlit for UI**: Rapid prototyping, built-in state management
6. **Query Parameters for Navigation**: Enables click-anywhere navigation on landing page

---

## 🐛 Known Issues & Solutions

1. **MoviePy Decorator Compatibility**: Fixed by pinning `decorator==4.4.1`
2. **Gemini Rate Limits**: Use `gemini-1.5-flash` for higher quotas
3. **Video Intelligence API**: Can be slow for long videos (use Fast Mode)
4. **Python 3.9 Compatibility**: Uses `compat_fix.py` shim for Google Cloud libraries

---

## 📊 Performance Considerations

- **Fast Mode**: Skips Video Intelligence API, uses only Gemini Vision (faster)
- **Frame Sampling**: Adjusts number of frames based on video duration
- **Chunked Processing**: Live streams processed in 10-second chunks
- **Caching**: Logo overlays cached to avoid reprocessing

---

## 🔐 Security Notes

- Service account keys stored in `.env` (not committed to repo)
- API keys loaded from environment variables
- No hardcoded credentials
- `.gitignore` excludes sensitive files

---

## 📝 For Demo Presentation

**5-Minute Demo Flow**:

1. **Landing Page** (10s): Show animated welcome screen
2. **Input** (30s): Paste YouTube URL or upload video
3. **Processing** (60s): Show progress bar, explain agent pipeline
4. **Results** (90s): Display highlight reel, segments, commentary
5. **Editor** (60s): Show iterative editing with chatbot
6. **Logo/Intro** (30s): Generate logo and intro video
7. **Final** (30s): Download and post to X

**Key Technical Points to Highlight**:
- Agent-based architecture
- Dual vision analysis (Video Intelligence + Gemini)
- Intelligent ranking system
- Smooth video transitions
- AI-generated commentary

---

## 📚 Additional Documentation

- `AGENTS.md`: Detailed agent documentation
- `API_KEYS_GUIDE.md`: Step-by-step API setup
- `PIPELINE_FLOW.md`: Visual pipeline flow diagrams
- `ARCHITECTURE.md`: System architecture details

---

**Built with ❤️ using Google Cloud AI Services**

