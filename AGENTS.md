# 🤖 Game Watcher AI - Agents Documentation

This document provides comprehensive documentation for all agents in the Game Watcher AI system.

## Table of Contents

- [Base Agent](#base-agent)
- [Input Agent](#input-agent)
- [Vision Agent](#vision-agent)
- [Planner Agent](#planner-agent)
- [Editor Agent](#editor-agent)
- [Commentator Agent](#commentator-agent)

---

## Base Agent

**Location:** `agents/base_agent.py`

### Overview
The `BaseAgent` class is an abstract base class that all other agents inherit from. It provides common functionality like logging and configuration management.

### Key Features
- **Abstract Interface**: Defines the `process()` method that all agents must implement
- **Logging**: Built-in logging functionality with agent-specific loggers
- **Configuration**: Accepts and stores configuration dictionaries

### Methods

#### `__init__(name: str, config: Optional[Dict] = None)`
Initializes the agent with a name and optional configuration.

**Parameters:**
- `name`: Agent identifier (e.g., "InputAgent", "VisionAgent")
- `config`: Optional configuration dictionary

#### `process(input_data: Any) -> Any`
Abstract method that must be implemented by all subclasses. Processes input data and returns results.

#### `log(message: str, level: str = "info")`
Logs a message using the agent's logger.

**Parameters:**
- `message`: Log message
- `level`: Log level ("info", "warning", "error", "debug")

---

## Input Agent

**Location:** `agents/input_agent.py`

### Overview
The `InputAgent` handles video input from multiple sources: YouTube URLs, uploaded files, and live streams. It's the first agent in the pipeline and prepares video content for analysis.

### Responsibilities
- Detect input source type (YouTube, file upload, live stream)
- Download YouTube videos using `yt-dlp`
- Validate uploaded files
- Set up live stream connections
- Return standardized video path and metadata

### Input Modes

#### 1. YouTube Mode
- Detects YouTube URLs (`youtube.com`, `youtu.be`)
- Downloads video using `YouTubeHandler`
- Handles 403 errors with custom headers and user agents
- Automatically renames files to `.mp4` extension

#### 2. Upload Mode
- Accepts local file paths
- Validates file existence
- Returns file path for processing

#### 3. Live Stream Mode
- Detects RTSP or stream URLs
- Sets up streaming connection
- Returns stream metadata (actual processing handled by `LiveStreamHandler`)

### Methods

#### `process(input_data: Union[str, Path]) -> dict`
Main processing method that detects input type and routes to appropriate handler.

**Input:**
- YouTube URL (string starting with `http://` or `https://`)
- File path (string or Path object)
- Stream URL (RTSP or stream URL)

**Output:**
```python
{
    "video_path": str,      # Path to video file
    "mode": str,            # "youtube", "upload", or "live"
    "source": str,          # Original input source
    "status": str           # "downloaded", "ready", or "streaming"
}
```

#### `_handle_youtube(url: str) -> dict`
Downloads video from YouTube using `YouTubeHandler`.

#### `_handle_file_upload(file_path: Path) -> dict`
Validates and processes uploaded video file.

#### `_handle_live_stream(stream_url: str) -> dict`
Sets up live stream connection.

### Dependencies
- `handlers.youtube_handler.YouTubeHandler`
- `handlers.live_stream_handler.LiveStreamHandler`

---

## Vision Agent

**Location:** `agents/vision_agent.py`

### Overview
The `VisionAgent` analyzes video content to detect plays, events, key frames, and crowd reactions. It uses Google Video Intelligence API and Gemini Vision for comprehensive video analysis.

### Responsibilities
- Analyze video using Google Video Intelligence API
- Sample and analyze key frames using Gemini Vision
- Detect sports events (goals, baskets, touchdowns, etc.)
- Identify successful vs. missed plays
- Detect crowd reactions and player visibility
- Extract shot changes and important moments

### Analysis Methods

#### 1. Video Intelligence API
Uses Google Cloud Video Intelligence API for:
- **Label Detection**: Identifies sports-related events (goals, baskets, etc.)
- **Shot Change Detection**: Finds scene transitions and camera cuts
- **Object Tracking**: Tracks objects (ball, players) through frames
- **Fast Mode**: For videos < 3 minutes, uses fewer features for speed

**Features Used:**
- `LABEL_DETECTION`: Detects sports events
- `SHOT_CHANGE_DETECTION`: Finds scene transitions
- `OBJECT_TRACKING`: Tracks moving objects (optional, for longer videos)

#### 2. Gemini Vision
Uses Gemini 2.0 Flash Vision model for:
- **Key Frame Analysis**: Analyzes sampled frames throughout the video
- **Event Detection**: Identifies specific plays and moments
- **Success Detection**: Determines if shots/goals were successful
- **Player Visibility**: Detects if players are visible in frames
- **Crowd Reaction**: Estimates crowd excitement level (0-10)

**Frame Sampling:**
- Evenly samples frames throughout entire video (not just beginning)
- More frames for longer videos (10-40 frames based on duration)
- Returns frame image, timestamp, and frame index

### Methods

#### `process(input_data: Union[str, Path, Dict]) -> Dict`
Main processing method that orchestrates video analysis.

**Input:**
- Video path (string or Path)
- Or dict with `video_path` and `mode`

**Output:**
```python
{
    "detections": {
        "key_frames": List[Dict],    # Key frame analysis results
        "events": List[Dict],        # Detected events
        "plays": List[Dict]          # Detected plays from Video Intelligence
    },
    "key_frames": List[Dict],
    "events": List[Dict],
    "plays": List[Dict],
    "metadata": {
        "video_path": str,
        "mode": str,
        "analysis_complete": bool
    }
}
```

#### `_analyze_with_video_intelligence(video_path: str) -> Dict`
Analyzes video using Google Video Intelligence API.

**Returns:**
- `key_frames`: Shot change detections
- `plays`: Sports-related events (goals, baskets, etc.)

#### `_analyze_with_gemini_vision(video_path: str, mode: str) -> Dict`
Analyzes key frames using Gemini Vision model.

**Returns:**
- `events`: List of detected events with:
  - `timestamp`: Event time in video
  - `description`: Event description
  - `is_successful`: Whether play was successful
  - `player_visible`: Whether player is visible
  - `crowd_reaction`: Excitement level (0-10)
  - `has_action`: Whether significant action occurred
  - `is_highlight`: Whether this is a highlight-worthy moment

### Configuration
- `use_video_intelligence`: Enable/disable Video Intelligence API (default: True)
- `use_gemini_vision`: Enable/disable Gemini Vision (default: True)

### Dependencies
- `google.cloud.videointelligence_v1`
- `google.generativeai`
- `utils.video_utils.sample_key_frames`
- `utils.video_utils.get_video_info`

---

## Planner Agent

**Location:** `agents/planner_agent.py`

### Overview
The `PlannerAgent` creates a structured plan for the highlight reel by ranking moments, removing duplicates, and organizing segments with proper timing and buffers.

### Responsibilities
- Collect all potential highlight moments from Vision Agent
- Rank moments by importance, excitement, and success
- Remove duplicate and overlapping segments
- Create segments with proper timing (pre/post buffers)
- Ensure ending/last play is always included
- Apply extended buffers for scoring plays to show shooter
- Add randomization for variation between runs

### Key Features

#### 1. Moment Collection
Collects moments from multiple sources:
- Events from Gemini Vision analysis
- Plays from Video Intelligence API
- Shot changes from Video Intelligence API
- Timeline-based segments (fallback)

#### 2. Ranking System
Ranks moments using a scoring system:

**Score Factors:**
- **Base Confidence**: Initial confidence from detection
- **Success Bonus**: +0.5 for successful plays
- **Ending Bonus**: +0.4 for moments in last 30 seconds
- **Action Bonus**: +0.2 for any detected action
- **Crowd Reaction**: +0.1 to +0.3 based on excitement level
- **Random Variation**: ±0.05 to avoid identical results

**Filtering:**
- Skips moments with score < 0.2
- Penalizes missed shots (but includes if crowd reaction is high)
- Prioritizes successful plays

#### 3. Segment Creation
Creates video segments with:
- **Pre-buffers**: Time before event starts
  - Regular events: 2 seconds
  - Scoring plays: 5-7 seconds (to show shooter)
  - Extended to 8 seconds if player is visible
- **Post-buffers**: 5 seconds after event (to show completion)
- **Minimum Duration**: 3 seconds
- **Maximum Duration**: 30 seconds
- **Overlap Detection**: Removes segments within 3 seconds of each other

#### 4. Fallback Mechanisms
If no ranked moments found, uses multiple fallbacks:
1. Use top 15 events from Gemini Vision
2. Use top 10 shot changes from Video Intelligence
3. Use top 10 plays from Video Intelligence
4. Create timeline-based segments (evenly spaced)
5. Create default segment from video start

#### 5. Ending Guarantee
Always ensures the last 15 seconds of video are included if not already covered.

### Methods

#### `process(input_data: Dict) -> Dict`
Main processing method that creates highlight plan.

**Input:**
```python
{
    "detections": Dict,
    "events": List[Dict],
    "plays": List[Dict],
    "key_frames": List[Dict],
    "metadata": {
        "video_path": str
    }
}
```

**Output:**
```python
{
    "plan": {
        "segments": List[Dict],
        "total_duration": float,
        "highlight_count": int,
        "ordering": str
    },
    "segments": List[Dict],  # Detailed segment information
    "metadata": {
        "total_moments_found": int,
        "highlights_selected": int
    }
}
```

#### `_collect_moments(events, plays, key_frames, input_data) -> List[Dict]`
Collects all potential highlight moments from various sources.

#### `_rank_moments(moments: List[Dict]) -> List[Dict]`
Ranks moments by importance and excitement.

#### `_create_segments(ranked_moments: List[Dict]) -> List[Dict]`
Creates video segments with proper timing and buffers.

### Configuration
- `min_duration`: Minimum highlight length (default: 3 seconds)
- `max_duration`: Maximum highlight length (default: 30 seconds)
- `pre_buffer`: Time before event (default: 2 seconds)
- `post_buffer`: Time after event (default: 5 seconds)
- `scoring_pre_buffer`: Time before scoring play (default: 5 seconds)

---

## Editor Agent

**Location:** `agents/editor_agent.py`

### Overview
The `EditorAgent` extracts video segments and compiles them into a final highlight reel with smooth fade transitions. It can optionally use Veo 3.1 for advanced video editing.

### Responsibilities
- Extract video segments from original video using MoviePy
- Optionally enhance clips using Veo 3.1
- Compile segments into final highlight reel
- Add smooth fade transitions between clips
- Handle edge cases (no segments, missing video path)

### Key Features

#### 1. Segment Extraction
- Extracts segments using MoviePy's `subclipped()` method
- Ensures segments don't exceed video duration
- Creates individual segment files (`segment_000.mp4`, etc.)
- Handles timing edge cases

#### 2. Veo Editing (Optional)
- Can enhance clips using Google Veo 3.1
- Applies cinematic effects, slow-motion, stabilization
- Currently placeholder (Veo API integration pending)

#### 3. Reel Compilation
- Compiles all segments into single highlight reel
- Adds smooth crossfade transitions between clips
- Uses overlapping clips with opacity blending for fades

**Transition Details:**
- **First Clip**: Fades out at end
- **Last Clip**: Fades in at start
- **Middle Clips**: Fade in at start AND fade out at end
- **Transition Duration**: 0.5 seconds (configurable)
- **Method**: Frame-level opacity blending using MoviePy's `fl()` method

#### 4. Error Handling
- Gracefully handles missing segments (returns "no_segments" status)
- Validates video path from multiple sources
- Falls back to simple concatenation if transitions fail

### Methods

#### `process(input_data: Dict) -> Dict`
Main processing method that extracts and compiles highlight reel.

**Input:**
```python
{
    "plan": Dict,
    "segments": List[Dict],
    "video_path": str,
    "metadata": {
        "video_path": str
    }
}
```

**Output:**
```python
{
    "highlight_reel": str,           # Path to final highlight reel
    "clips": List[str],              # Paths to individual segments
    "segment_count": int,
    "status": str                    # "complete" or "no_segments"
}
```

#### `_extract_segments(video_path: str, segments: List[Dict]) -> List[Path]`
Extracts video segments from original video.

**Process:**
1. Loads source video with MoviePy
2. For each segment, extracts clip using `subclipped(start, end)`
3. Saves individual segment files
4. Returns list of segment file paths

#### `_edit_with_veo(clips: List[Path], segments: List[Dict]) -> List[Path]`
Enhances clips using Veo 3.1 (placeholder implementation).

#### `_compile_reel(clips: List[Path], source_video: str) -> Path`
Compiles all segments into final highlight reel with fade transitions.

**Process:**
1. Loads all segment clips
2. Applies fade effects to each clip:
   - First clip: fade out at end
   - Last clip: fade in at start
   - Middle clips: fade in and fade out
3. Positions clips to overlap for crossfade effect
4. Composites all clips using `CompositeVideoClip`
5. Exports final reel as MP4

### Configuration
- `enable_veo`: Enable Veo editing (default: True)
- `output_dir`: Directory for output files (default: "outputs")

### Dependencies
- `moviepy` (VideoFileClip, CompositeVideoClip, concatenate_videoclips, ColorClip)
- `numpy` (for frame manipulation

---

## Commentator Agent

**Location:** `agents/commentator_agent.py`

### Overview
The `CommentatorAgent` generates text and audio commentary for highlight segments using Gemini AI and text-to-speech.

### Responsibilities
- Generate exciting commentary text for each highlight segment
- Create overall narration for the highlight reel
- Convert text to speech using gTTS
- Synchronize commentary with video timestamps
- Handle API rate limits gracefully

### Key Features

#### 1. Segment Commentary
- Generates 1-2 sentences of energetic commentary per segment
- Uses segment description and importance score
- Matches energy level to importance
- Includes segment position in reel

#### 2. Overall Narration
- Creates introduction for highlight reel
- Mentions highlight count and total duration
- Sets the stage for highlights

#### 3. Text-to-Speech
- Converts commentary to audio using Google Text-to-Speech (gTTS)
- Combines narration and segment commentaries
- Exports as MP3 file

#### 4. Rate Limiting
- Currently uses `gemini-2.0-flash-exp` (10 requests/minute limit)
- Can hit rate limits with many segments
- Falls back to generic commentary on errors

### Methods

#### `process(input_data: Dict) -> Dict`
Main processing method that generates all commentary.

**Input:**
```python
{
    "plan": Dict,
    "segments": List[Dict],
    "highlight_reel": str
}
```

**Output:**
```python
{
    "commentaries": List[Dict],      # Commentary for each segment
    "overall_narration": str,        # Introduction narration
    "audio_file": str,               # Path to commentary audio
    "status": str                    # "complete" or "no_segments"
}
```

#### `_generate_segment_commentary(segment: Dict, index: int, total: int) -> Dict`
Generates commentary for a single segment.

**Returns:**
```python
{
    "segment_index": int,
    "text": str,                     # Commentary text
    "timestamp": float,             # Event time in video
    "segment_start": float,         # Full segment start time
    "duration": float               # Segment duration
}
```

#### `_generate_overall_narration(plan: Dict, segments: List[Dict]) -> str`
Generates introduction narration for the highlight reel.

#### `_generate_audio(commentaries: List[Dict], narration: str) -> Optional[Path]`
Converts all commentary to audio using gTTS.

**Process:**
1. Generates TTS for narration
2. Generates TTS for each segment commentary
3. Combines all audio segments
4. Exports as MP3 file

### Configuration
- `enable_tts`: Enable text-to-speech (default: True)
- `output_dir`: Directory for output files (default: "outputs")

### Dependencies
- `google.generativeai` (Gemini API)
- `gtts` (Google Text-to-Speech)
- `pydub` (Audio processing)

### Known Issues
- **Rate Limiting**: `gemini-2.0-flash-exp` has 10 requests/minute limit
- **Solution**: Switch to `gemini-1.5-flash` or `gemini-2.0-flash-preview` for higher quotas

---

## Agent Interaction Summary

```
InputAgent → VisionAgent → PlannerAgent → EditorAgent → CommentatorAgent
    ↓            ↓              ↓             ↓              ↓
  Video      Analysis      Segments      Highlight      Commentary
  Path       Results        Plan          Reel           Audio
```

Each agent:
1. Receives input from previous agent
2. Processes data using its specialized capabilities
3. Returns structured output for next agent
4. Handles errors gracefully with fallbacks

---

## Extension Points

To add a new agent:

1. **Create Agent Class**: Inherit from `BaseAgent`
2. **Implement `process()` method**: Define input/output format
3. **Add to Pipeline**: Import and initialize in `pipeline.py`
4. **Update Documentation**: Add to this file

Example:
```python
class NewAgent(BaseAgent):
    def __init__(self, config=None):
        super().__init__("NewAgent", config)
    
    def process(self, input_data):
        # Process input_data
        return {"result": "processed"}
```

