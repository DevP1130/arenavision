# 🏗️ Game Watcher AI - Architecture

## System Overview

Game Watcher AI is an **agentic AI system** that automatically watches sports games and generates highlight reels with commentary. It uses a multi-agent architecture powered by Google Cloud AI services.

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Agent                               │
│  Handles: YouTube URLs, File Uploads, Live Streams          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vision Agent                              │
│  Uses: Video Intelligence API + Gemini Vision               │
│  Detects: Plays, Events, Key Frames, Crowd Reactions        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Planner Agent                            │
│  Creates: Highlight plan, Segment ordering, Timing          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Editor Agent                              │
│  Uses: Veo 3.1 for video editing                            │
│  Creates: Highlight clips, Final reel                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Commentator Agent                           │
│  Uses: Gemini 2.0 Flash + TTS                                │
│  Generates: Text commentary + Audio narration               │
└─────────────────────────────────────────────────────────────┘
```

## Input Modes

### 🎥 Mode 1: YouTube / Upload
- **Input**: YouTube URL or uploaded MP4 file
- **Processing**: Full video analysis
- **Use Case**: Demo-friendly, post-game analysis
- **Flow**: Download → Analyze → Plan → Edit → Commentate

### 📡 Mode 2: Live Stream
- **Input**: RTSP/HLS stream URL
- **Processing**: Real-time chunk-based analysis
- **Use Case**: Live game monitoring, real-time highlights
- **Flow**: Connect → Capture chunks → Analyze → Detect events → Generate highlights

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Vision** | Google Video Intelligence API | Play detection, shot changes, object tracking |
| **Vision** | Gemini 2.0 Flash Vision | Key frame analysis, event detection |
| **Reasoning** | Google ADK / Agent Framework | Multi-agent orchestration |
| **Editing** | Veo 3.1 | Video enhancement, transitions, slow-mo |
| **Graphics** | Imagen 3 | Overlays, graphics, scoreboards |
| **Commentary** | Gemini 2.0 Flash | Text generation |
| **Audio** | gTTS | Text-to-speech narration |
| **Frontend** | Streamlit | Web interface |
| **Video Processing** | OpenCV, MoviePy | Frame extraction, compilation |

## Data Flow

### YouTube/Upload Mode
```
User Input (URL/File)
    ↓
InputAgent → Downloads/Loads video
    ↓
VisionAgent → Analyzes full video
    ├─ Video Intelligence API (labels, shots, objects)
    └─ Gemini Vision (key frames, events)
    ↓
PlannerAgent → Ranks moments, creates segments
    ↓
EditorAgent → Extracts & edits clips with Veo
    ↓
CommentatorAgent → Generates commentary
    ↓
Final Output: Highlight reel + Commentary audio
```

### Live Stream Mode
```
Stream URL
    ↓
LiveStreamHandler → Connects & captures chunks (10s each)
    ↓
For each chunk:
    VisionAgent → Real-time analysis
    PlannerAgent → Update highlight plan
    EditorAgent → Save potential highlights
    CommentatorAgent → Generate live commentary
    ↓
Final Output: Compiled highlights + Live commentary feed
```

## Key Components

### Agents (`agents/`)

1. **InputAgent**: Handles multiple input sources
   - YouTube download via yt-dlp
   - File upload handling
   - Live stream setup

2. **VisionAgent**: Video analysis
   - Video Intelligence API integration
   - Gemini Vision frame analysis
   - Event detection and scoring

3. **PlannerAgent**: Highlight planning
   - Moment ranking by importance
   - Segment creation with timing
   - Highlight reel structure

4. **EditorAgent**: Video editing
   - Segment extraction with MoviePy
   - Veo 3.1 integration for enhancement
   - Reel compilation

5. **CommentatorAgent**: Commentary generation
   - Gemini-powered text generation
   - TTS audio generation
   - Timestamp synchronization

### Handlers (`handlers/`)

- **YouTubeHandler**: Downloads videos from YouTube
- **LiveStreamHandler**: Captures and processes live streams

### Pipeline (`pipeline.py`)

- **GameWatcherPipeline**: Main orchestrator
  - Coordinates all agents
  - Handles both input modes
  - Manages error handling and logging

### Frontend (`app.py`)

- **Streamlit Interface**:
  - Dual mode selection
  - Progress tracking
  - Results display
  - Video/audio playback
  - Download functionality

## Configuration

All configuration is managed through:
- `config.py`: Centralized settings
- `.env`: Environment variables (API keys, paths)
- Agent-specific configs passed during initialization

## Output Structure

```
outputs/
├── highlight_reel.mp4      # Final compiled highlights
├── commentary.mp3           # Audio commentary
└── segment_*.mp4            # Individual highlight clips
```

## Extensibility

The system is designed for easy extension:

1. **New Agents**: Inherit from `BaseAgent`
2. **New Input Sources**: Add handlers in `handlers/`
3. **New AI Models**: Integrate in respective agents
4. **Custom Processing**: Add steps in `pipeline.py`

## Performance Considerations

- **Video Intelligence API**: Async processing with timeouts
- **Live Mode**: Chunk-based processing to manage memory
- **Caching**: Reuse analysis results when possible
- **Parallel Processing**: Can process multiple segments concurrently

## Future Enhancements

- Real-time dashboard for live mode
- Multi-sport specialization
- Custom highlight templates
- Social media integration
- Advanced Veo editing prompts
- Player recognition and tracking

