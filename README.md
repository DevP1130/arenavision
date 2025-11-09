# 🎥 ArenaVision - Intelligent Sports Highlight Generation

**Intelligent sports highlight generation with agentic AI**

ArenaVision is an AI-powered system that automatically analyzes sports videos, detects key moments, creates highlight reels, and generates commentary using Google Cloud's advanced AI services.

## 🎬 Demo Video

Watch the full demonstration: [ArenaVision Demo](https://www.youtube.com/watch?v=RGqd40ZZlAg)

## 🎯 Features

- **Multi-Input Support**: YouTube URLs, file uploads, and live streams
- **Agentic AI Architecture**: Specialized AI agents for each processing stage
- **Dual Vision Analysis**: Combines Google Video Intelligence API + Gemini Vision
- **Intelligent Highlight Detection**: Automatically ranks and selects best moments
- **Smooth Video Editing**: Creates highlight reels with fade transitions
- **AI Commentary**: Generates text and audio commentary for highlights
- **Interactive Editing**: Chatbot-powered iterative video refinement
- **Logo & Intro Generation**: Creates custom logos (Imagen 3) and intro videos (Veo 3.1)
- **Social Media Integration**: Direct posting to X (Twitter)

## 🖼️ Screenshots

### Main Interface - Video Input & Processing
![Main Interface](./screencapture-localhost-8501-2025-11-09-11_11_32.png)
*Primary screen showing video input options and processing controls. View and download individual highlight segments with descriptions and timestamps. Iterative editing with chatbot assistance — remove segments, trim clips, and refine highlight.
*

### Logo & Intro Video Generation
![Logo & Intro](./screencapture-localhost-8501-2025-11-09-11_13_39.png)
*Generate custom logos using Imagen 3 and create intro videos with Veo 3.1*

### Final Video & Social Sharing
![Final Video](./screencapture-localhost-8501-2025-11-09-11_15_47.png)
*Review final highlight reel, download, and post directly to X (Twitter)*

## 🏗️ Architecture

ArenaVision uses a **multi-agent pipeline architecture** where specialized agents process video through sequential stages:

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

## 🚀 Quick Start

### 1. Install Dependencies

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

### 2. Set Up API Keys

Create a `.env` file in the project root:

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

### 3. Service Account Setup

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com)
2. Grant roles:
   - Vertex AI User
   - Video Intelligence API User
3. Download JSON key file
4. Set `GOOGLE_APPLICATION_CREDENTIALS` path in `.env`

### 4. Enable APIs

Enable in Google Cloud Console:
- Video Intelligence API
- Vertex AI API
- Generative AI API

### 5. Test Configuration

```bash
python test_keys.py
```

### 6. Run the Application

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 📊 How It Works

### Step 1: Input Processing
- **YouTube Mode**: Downloads video using `yt-dlp` with custom headers
- **Upload Mode**: Validates and processes uploaded video files
- **Live Stream Mode**: Connects to RTSP streams for real-time processing

### Step 2: Video Analysis
- **Video Intelligence API**: Detects sports events, shot changes, and objects
- **Gemini Vision**: Analyzes key frames for context, player visibility, and crowd reactions
- **Dual Analysis**: Combines structured detection with contextual understanding

### Step 3: Highlight Planning
- **Moment Collection**: Gathers all potential highlights from multiple sources
- **Intelligent Ranking**: Scores moments based on:
  - Success (made vs missed shots)
  - Crowd reaction (excitement level)
  - Timing (endings prioritized)
  - Action detection
- **Segment Creation**: Creates video segments with proper pre/post buffers

### Step 4: Video Editing
- **Segment Extraction**: Extracts individual highlight clips
- **Reel Compilation**: Combines segments with smooth fade transitions
- **Quality Optimization**: Ensures proper timing and flow

### Step 5: Commentary Generation
- **Text Generation**: Creates exciting commentary using Gemini AI
- **Audio Synthesis**: Converts to speech using Google Text-to-Speech
- **Synchronization**: Matches commentary to video timestamps

## 🎨 UI Features

### Modern Sports Theme
- **Purple Gradient Design**: Professional sports aesthetic
- **Oswald & Montserrat Fonts**: Modern, bold typography
- **Animated Backgrounds**: Subtle particle effects
- **Smooth Transitions**: Polished user experience

### Interactive Elements
- **Click-Anywhere Navigation**: Landing page supports full-screen clicking
- **Iterative Editing**: Chatbot-powered video refinement
- **Real-time Progress**: Visual progress bars during processing
- **Responsive Design**: Works on various screen sizes

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

## 🔑 API Keys Setup

**You need 3 things:**

1. **GOOGLE_API_KEY** - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **GOOGLE_CLOUD_PROJECT** - Your project ID from Google Cloud Console
3. **GOOGLE_APPLICATION_CREDENTIALS** - Service account JSON file

📖 **Detailed instructions**: See `API_KEYS_GUIDE.md` for complete setup guide.

## 🔧 Configuration

Set up your Google Cloud project and enable:
- Video Intelligence API
- Vertex AI
- Generative AI APIs (Gemini, Veo, Imagen)

## 🎯 Key Features Explained

### Fast Mode
- Skips Video Intelligence API for faster processing
- Uses only Gemini Vision analysis
- Ideal for short videos or quick demos

### Iterative Editing
- Chatbot-powered video refinement
- Natural language commands:
  - "Remove the second segment"
  - "Trim 5 seconds from the end"
  - "Reorder clips by excitement"
- Maintains edit history for undo/redo

### Logo & Intro Generation
- **Logo Generation**: Uses Imagen 3 (WHISK) to create custom logos
- **Intro Videos**: Uses Veo 3.1 to generate 5-second intro videos
- **Customization**: Text overlays and background descriptions

### Social Media Integration
- Direct posting to X (Twitter)
- Automatic video upload and caption
- OAuth authentication

## 🐛 Troubleshooting

### Common Issues:

1. **MoviePy Import Error**
   - Solution: Install `decorator==4.4.1` (compatibility fix)

2. **Video Intelligence API Slow**
   - Solution: Use Fast Mode for quicker processing

3. **Gemini Rate Limits**
   - Solution: Switch to `gemini-1.5-flash` for higher quotas

4. **Python 3.9 Compatibility**
   - Solution: Uses `compat_fix.py` shim for Google Cloud libraries

## 📚 Documentation

- `TECHNICAL_README.md`: Comprehensive technical documentation
- `AGENTS.md`: Detailed agent documentation
- `API_KEYS_GUIDE.md`: Step-by-step API setup
- `PIPELINE_FLOW.md`: Visual pipeline flow diagrams
- `ARCHITECTURE.md`: System architecture details

## 🎬 Demo Flow

**5-Minute Demo Structure**:

1. **Landing Page** (10s): Animated welcome screen
2. **Input** (30s): Paste YouTube URL or upload video
3. **Processing** (60s): Show progress bar, explain agent pipeline
4. **Results** (90s): Display highlight reel, segments, commentary
5. **Editor** (60s): Show iterative editing with chatbot
6. **Logo/Intro** (30s): Generate logo and intro video
7. **Final** (30s): Download and post to X

## 🔐 Security Notes

- Service account keys stored in `.env` (not committed to repo)
- API keys loaded from environment variables
- No hardcoded credentials
- `.gitignore` excludes sensitive files

## 📝 License

This project is part of a hackathon submission.

## 🤝 Contributing

This is a hackathon project. For questions or issues, please refer to the documentation files.

---

**Built with ❤️ using Google Cloud AI Services**

For detailed technical information, see `TECHNICAL_README.md`
