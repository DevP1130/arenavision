# 🔄 Game Watcher AI - Pipeline Flow & Agent Interactions

This document explains how all agents work together in the Game Watcher AI pipeline to transform raw video input into polished highlight reels with commentary.

## Table of Contents

- [Pipeline Overview](#pipeline-overview)
- [Data Flow Diagram](#data-flow-diagram)
- [Step-by-Step Flow](#step-by-step-flow)
- [Agent Communication](#agent-communication)
- [Input Modes](#input-modes)
- [Error Handling](#error-handling)
- [Output Structure](#output-structure)

---

## Pipeline Overview

The Game Watcher AI pipeline is a **sequential multi-agent system** where each agent processes data and passes results to the next agent. The pipeline is orchestrated by the `GameWatcherPipeline` class.

### Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GameWatcherPipeline                          │
│                    (Orchestrator)                               │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  InputAgent   │──▶│  VisionAgent  │──▶│ PlannerAgent │
└───────────────┘   └───────────────┘   └───────────────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ EditorAgent   │──▶│CommentatorAgent│──▶│ Final Output  │
└───────────────┘   └───────────────┘   └───────────────┘
```

---

## Data Flow Diagram

### Complete Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: InputAgent                                          │
│ ───────────────────────────────────────────────────────────│
│ Input: YouTube URL / File Path / Stream URL                │
│ Process: Detect type → Download/Validate → Return path     │
│ Output: {video_path, mode, source, status}                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: VisionAgent                                         │
│ ───────────────────────────────────────────────────────────│
│ Input: {video_path, mode, ...}                            │
│ Process:                                                    │
│   • Video Intelligence API → Labels, Shots, Objects         │
│   • Gemini Vision → Key frames, Events, Success detection  │
│ Output: {detections, events, plays, key_frames, metadata}  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: PlannerAgent                                       │
│ ───────────────────────────────────────────────────────────│
│ Input: {detections, events, plays, key_frames, metadata}  │
│ Process:                                                    │
│   • Collect all moments                                    │
│   • Rank by importance/excitement                           │
│   • Remove duplicates/overlaps                             │
│   • Create segments with buffers                            │
│   • Ensure ending is included                              │
│ Output: {plan, segments, metadata}                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: EditorAgent                                        │
│ ───────────────────────────────────────────────────────────│
│ Input: {plan, segments, video_path, metadata}             │
│ Process:                                                    │
│   • Extract segments from video                             │
│   • (Optional) Enhance with Veo                             │
│   • Compile reel with fade transitions                     │
│ Output: {highlight_reel, clips, segment_count, status}     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: CommentatorAgent                                   │
│ ───────────────────────────────────────────────────────────│
│ Input: {plan, segments, highlight_reel}                     │
│ Process:                                                    │
│   • Generate commentary for each segment                    │
│   • Generate overall narration                              │
│   • Convert to audio (TTS)                                  │
│ Output: {commentaries, overall_narration, audio_file}      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
              Final Results
```

---

## Step-by-Step Flow

### Step 1: Input Processing (InputAgent)

**Purpose**: Prepare video for analysis

**Input**: 
- YouTube URL: `"https://youtube.com/watch?v=..."`
- File Path: `"/path/to/video.mp4"`
- Stream URL: `"rtsp://stream.url"`

**Process**:
1. Detects input type (URL pattern matching)
2. Routes to appropriate handler:
   - **YouTube**: Downloads using `YouTubeHandler` with custom headers
   - **File**: Validates file exists
   - **Stream**: Sets up connection metadata
3. Returns standardized output

**Output**:
```python
{
    "video_path": "/path/to/video.mp4",
    "mode": "youtube" | "upload" | "live",
    "source": "original_input",
    "status": "downloaded" | "ready" | "streaming"
}
```

**Next Agent**: VisionAgent

---

### Step 2: Video Analysis (VisionAgent)

**Purpose**: Extract meaningful events and moments from video

**Input**: Output from InputAgent

**Process**:
1. **Video Intelligence API** (if enabled):
   - Analyzes full video for labels (goals, baskets, etc.)
   - Detects shot changes (scene transitions)
   - Tracks objects (ball, players)
   - Uses "fast mode" for videos < 3 minutes

2. **Gemini Vision** (if enabled):
   - Samples key frames evenly throughout video
   - Analyzes each frame for:
     - Event type (basket, goal, etc.)
     - Success (made vs. missed)
     - Player visibility
     - Crowd reaction (0-10)
     - Action presence

**Output**:
```python
{
    "detections": {
        "key_frames": [...],    # Shot changes
        "events": [...],        # Gemini Vision events
        "plays": [...]         # Video Intelligence plays
    },
    "events": [
        {
            "timestamp": 45.2,
            "description": "Three-point basket made",
            "is_successful": True,
            "player_visible": True,
            "crowd_reaction": 8,
            "has_action": True,
            "is_highlight": True
        },
        ...
    ],
    "plays": [...],
    "key_frames": [...],
    "metadata": {
        "video_path": "/path/to/video.mp4",
        "mode": "youtube",
        "analysis_complete": True
    }
}
```

**Next Agent**: PlannerAgent

---

### Step 3: Highlight Planning (PlannerAgent)

**Purpose**: Create structured plan for highlight reel

**Input**: Output from VisionAgent

**Process**:
1. **Collect Moments**:
   - Gathers events from Gemini Vision
   - Gathers plays from Video Intelligence
   - Gathers shot changes
   - Marks moments in last 30 seconds as "ending"

2. **Rank Moments**:
   - Scores each moment:
     - Base confidence
     - +0.5 for successful plays
     - +0.4 for ending moments
     - +0.2 for action
     - +0.1-0.3 for crowd reaction
     - ±0.05 random variation
   - Filters out low-scoring moments (< 0.2)
   - Sorts by score (highest first)

3. **Create Segments**:
   - For each ranked moment:
     - Calculates start time (event_time - pre_buffer)
     - Calculates end time (event_time + post_buffer)
     - **Scoring plays**: Uses 5-8 second pre-buffer (to show shooter)
     - **Regular events**: Uses 2 second pre-buffer
     - Removes duplicates (within 3 seconds)
   - Ensures ending is included (last 15 seconds)

4. **Fallback Mechanisms** (if no ranked moments):
   - Try top events from Gemini
   - Try top shot changes
   - Try top plays
   - Create timeline-based segments
   - Create default segment

**Output**:
```python
{
    "plan": {
        "segments": [...],
        "total_duration": 120.5,
        "highlight_count": 6,
        "ordering": "chronological"
    },
    "segments": [
        {
            "start_time": 38.0,      # With pre-buffer
            "end_time": 50.0,        # With post-buffer
            "duration": 12.0,
            "event_start": 43.0,     # Actual event time
            "event_end": 45.0,
            "type": "basket",
            "description": "Three-point basket made",
            "importance": 0.85
        },
        ...
    ],
    "metadata": {
        "total_moments_found": 15,
        "highlights_selected": 6
    }
}
```

**Next Agent**: EditorAgent

---

### Step 4: Video Editing (EditorAgent)

**Purpose**: Extract segments and compile highlight reel

**Input**: Output from PlannerAgent + video_path

**Process**:
1. **Extract Segments**:
   - Loads source video with MoviePy
   - For each segment:
     - Extracts clip using `subclipped(start_time, end_time)`
     - Saves as `segment_000.mp4`, `segment_001.mp4`, etc.

2. **Optional Veo Editing**:
   - Enhances clips with Veo 3.1 (placeholder)
   - Applies cinematic effects

3. **Compile Reel**:
   - Loads all segment clips
   - Applies fade transitions:
     - First clip: fades out at end
     - Last clip: fades in at start
     - Middle clips: fade in and fade out
   - Overlaps clips for crossfade effect (0.5s overlap)
   - Composites using `CompositeVideoClip`
   - Exports as `highlight_reel.mp4`

**Output**:
```python
{
    "highlight_reel": "/path/to/outputs/highlight_reel.mp4",
    "clips": [
        "/path/to/outputs/segment_000.mp4",
        "/path/to/outputs/segment_001.mp4",
        ...
    ],
    "segment_count": 6,
    "status": "complete"
}
```

**Next Agent**: CommentatorAgent

---

### Step 5: Commentary Generation (CommentatorAgent)

**Purpose**: Generate text and audio commentary

**Input**: Output from PlannerAgent + EditorAgent

**Process**:
1. **Segment Commentary**:
   - For each segment:
     - Generates 1-2 sentences using Gemini
     - Uses segment description and importance
     - Matches energy to importance score
   - Handles rate limits gracefully

2. **Overall Narration**:
   - Generates introduction for reel
   - Mentions highlight count and duration

3. **Text-to-Speech**:
   - Converts narration to audio (gTTS)
   - Converts each segment commentary to audio
   - Combines all audio segments
   - Exports as `commentary.mp3`

**Output**:
```python
{
    "commentaries": [
        {
            "segment_index": 0,
            "text": "Incredible three-pointer from downtown!",
            "timestamp": 43.0,
            "segment_start": 38.0,
            "duration": 12.0
        },
        ...
    ],
    "overall_narration": "Welcome to the game highlights! Here are the top 6 moments...",
    "audio_file": "/path/to/outputs/commentary.mp3",
    "status": "complete"
}
```

**Final Output**: Combined results from all agents

---

## Agent Communication

### Data Passing

Agents communicate through **structured dictionaries**. Each agent:
1. Receives input from previous agent
2. Adds its own results
3. Passes combined data to next agent

### Data Structure Evolution

```
InputAgent Output:
{
    "video_path": str,
    "mode": str,
    ...
}
    ↓
VisionAgent adds:
{
    "video_path": str,        # Passed through
    "mode": str,              # Passed through
    "detections": {...},      # NEW
    "events": [...],          # NEW
    "metadata": {...}         # NEW
}
    ↓
PlannerAgent adds:
{
    ... (all previous data)   # Passed through
    "plan": {...},            # NEW
    "segments": [...]         # NEW
}
    ↓
EditorAgent receives:
{
    "plan": {...},
    "segments": [...],
    "video_path": str,        # From InputAgent
    "metadata": {
        "video_path": str     # Also here
    }
}
```

### Metadata Preservation

The pipeline preserves metadata throughout:
- `video_path` is passed through all agents
- `mode` is preserved for context
- `metadata` dictionary accumulates information

---

## Input Modes

### 1. YouTube Mode

```
User Input: "https://youtube.com/watch?v=..."
    ↓
InputAgent: Downloads video using yt-dlp
    ↓
VisionAgent: Analyzes downloaded video
    ↓
... (rest of pipeline)
```

**Characteristics**:
- Full video analysis
- All features enabled
- Can take 1-3 minutes for Video Intelligence API

### 2. Upload Mode

```
User Input: "/path/to/video.mp4"
    ↓
InputAgent: Validates file exists
    ↓
VisionAgent: Analyzes uploaded video
    ↓
... (rest of pipeline)
```

**Characteristics**:
- Same as YouTube mode
- Faster (no download step)
- Local file processing

### 3. Live Stream Mode

```
User Input: "rtsp://stream.url"
    ↓
InputAgent: Sets up stream connection
    ↓
LiveStreamHandler: Captures chunks (10s each)
    ↓
For each chunk:
    VisionAgent → PlannerAgent → EditorAgent → CommentatorAgent
    ↓
Final: Compiled highlights from all chunks
```

**Characteristics**:
- Real-time processing
- Chunk-based analysis
- Continuous highlight detection
- Lower latency

---

## Error Handling

### Pipeline-Level Error Handling

The pipeline handles errors at multiple levels:

1. **Agent-Level**: Each agent has try/except blocks
2. **Pipeline-Level**: Catches exceptions and returns error status
3. **Fallback Mechanisms**: Multiple fallbacks in PlannerAgent

### Error Flow

```
Agent Error
    ↓
Agent logs error
    ↓
Agent returns error status or fallback result
    ↓
Pipeline checks status
    ↓
If critical error: Stop pipeline, return error
If recoverable: Continue with fallback
```

### Common Error Scenarios

1. **No Highlights Detected**:
   - PlannerAgent: Uses fallback mechanisms
   - EditorAgent: Returns "no_segments" status
   - Pipeline: Returns "no_highlights" with helpful message

2. **API Rate Limits**:
   - CommentatorAgent: Falls back to generic commentary
   - VisionAgent: Can disable Video Intelligence API

3. **Missing Video Path**:
   - EditorAgent: Checks multiple locations
   - Pipeline: Passes video_path through metadata

4. **Download Failures**:
   - InputAgent: Raises error with helpful message
   - Pipeline: Catches and returns error status

---

## Output Structure

### Final Pipeline Output

```python
{
    "input_source": "original_input",
    "mode": "youtube" | "upload" | "live",
    "status": "complete" | "error" | "no_highlights",
    
    # From InputAgent
    "input": {
        "video_path": str,
        "mode": str,
        "source": str,
        "status": str
    },
    
    # From VisionAgent
    "vision": {
        "detections": {...},
        "events": [...],
        "plays": [...],
        "metadata": {...}
    },
    
    # From PlannerAgent
    "planner": {
        "plan": {...},
        "segments": [...],
        "metadata": {...}
    },
    
    # From EditorAgent
    "editor": {
        "highlight_reel": str,
        "clips": [...],
        "segment_count": int,
        "status": str
    },
    
    # From CommentatorAgent
    "commentary": {
        "commentaries": [...],
        "overall_narration": str,
        "audio_file": str,
        "status": str
    },
    
    # Final Summary
    "highlight_reel": str,              # Path to final video
    "commentary_audio": str,            # Path to audio
    "commentaries": [...],              # Commentary data
    "summary": {
        "highlights_found": int,
        "total_duration": float,
        "output_file": str
    }
}
```

### File Outputs

```
outputs/
├── highlight_reel.mp4      # Final compiled highlights
├── commentary.mp3          # Audio commentary
├── segment_000.mp4         # Individual highlight clips
├── segment_001.mp4
└── ...
```

---

## Performance Considerations

### Processing Time

- **Input**: < 1 second (download can take longer)
- **Vision**: 10-180 seconds (depends on video length and features)
- **Planning**: < 1 second
- **Editing**: 5-30 seconds (depends on segment count)
- **Commentary**: 5-20 seconds (depends on segment count and API limits)

**Total**: ~30 seconds to 4 minutes for typical videos

### Optimization Strategies

1. **Fast Mode**: Disable Video Intelligence API for faster processing
2. **Chunk Processing**: Live mode processes in 10-second chunks
3. **Parallel Processing**: Can process segments concurrently (future)
4. **Caching**: Reuse analysis results when possible (future)

---

## Extension Points

### Adding New Agents

1. **Create Agent**: Inherit from `BaseAgent`
2. **Add to Pipeline**: Import and initialize in `GameWatcherPipeline`
3. **Insert in Flow**: Add between existing agents or at end
4. **Update Flow**: Modify `process()` method in pipeline

### Modifying Flow

The pipeline flow can be modified in `pipeline.py`:
- Reorder agents
- Add conditional logic
- Skip agents based on conditions
- Add parallel processing

---

## Summary

The Game Watcher AI pipeline is a **sequential multi-agent system** that:

1. **InputAgent** prepares video for analysis
2. **VisionAgent** detects events and moments
3. **PlannerAgent** creates highlight plan
4. **EditorAgent** compiles highlight reel
5. **CommentatorAgent** generates commentary

Each agent:
- Receives structured input
- Processes using specialized capabilities
- Returns structured output
- Handles errors gracefully

The pipeline orchestrates all agents, manages data flow, and produces final highlight reels with commentary.

