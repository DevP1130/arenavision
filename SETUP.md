# 🚀 Setup Guide

## Prerequisites

1. **Python 3.9+** installed
2. **Google Cloud Account** with the following APIs enabled:
   - Video Intelligence API
   - Vertex AI
   - Generative AI APIs (Gemini, Veo, Imagen)

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google Cloud

1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the required APIs:
   ```bash
   gcloud services enable videointelligence.googleapis.com
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable generativelanguage.googleapis.com
   ```

3. Create a service account and download credentials:
   ```bash
   gcloud iam service-accounts create game-watcher-ai
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:game-watcher-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/aiplatform.user"
   
   gcloud iam service-accounts keys create service-account-key.json \
     --iam-account=game-watcher-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. Get your Google API key from https://makersuite.google.com/app/apikey

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GOOGLE_API_KEY=your-google-api-key

# Video Processing
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
TEMP_DIR=temp
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### YouTube Mode
1. Select "🎥 YouTube / Upload" mode
2. Paste a YouTube URL or upload a video file
3. Click "Process" and wait for analysis
4. Download the generated highlight reel

### Live Stream Mode
1. Select "📡 Live Stream" mode
2. Enter a stream URL (RTSP, HLS, etc.)
3. Set processing duration
4. Click "Start Live Processing"

## Testing

For testing without real streams, you can:
- Use a short YouTube video
- Upload a local video file
- Use a prerecorded video in "live" mode to simulate streaming

## Troubleshooting

### Video Intelligence API Errors
- Ensure the API is enabled in your Google Cloud project
- Check that your service account has proper permissions
- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid credentials

### Gemini API Errors
- Verify `GOOGLE_API_KEY` is set correctly
- Check API quota limits
- Ensure Gemini API is enabled

### Video Processing Errors
- Install `ffmpeg` for video processing:
  ```bash
  # macOS
  brew install ffmpeg
  
  # Ubuntu/Debian
  sudo apt-get install ffmpeg
  ```

## Architecture

```
app.py (Streamlit UI)
    ↓
pipeline.py (Orchestrator)
    ↓
agents/
    ├── input_agent.py      # Handles video input
    ├── vision_agent.py     # Analyzes video
    ├── planner_agent.py    # Plans highlights
    ├── editor_agent.py       # Edits video (Veo)
    └── commentator_agent.py # Generates commentary
```

