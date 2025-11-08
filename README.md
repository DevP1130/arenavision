# 🎥 Game Watcher AI Agent

An intelligent agentic AI system that watches sports games and automatically generates highlight reels with commentary.

## 🎯 Features

- **Dual Input Modes**: 
  - 🎥 On-Demand (YouTube/Uploaded Video)
  - 📡 Live Stream Mode
- **Multi-Agent Architecture**: Input → Vision → Planner → Editor → Commentator
- **Google Cloud Integration**: Video Intelligence, Gemini, Veo 3.1, Imagen 3
- **Real-time Analysis**: Automatic play detection and highlight generation

## 🏗️ Architecture

```
Input Agent (YouTube/Live) 
    ↓
Vision Agent (Video Intelligence / Gemini Vision)
    ↓
Planner Agent (Highlight ordering)
    ↓
Editor Agent (Veo 3.1 editing)
    ↓
Commentator Agent (Gemini + TTS)
```

## 🚀 Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up API keys** (see detailed guide below):
   - Create a `.env` file with your Google Cloud credentials
   - See `API_KEYS_GUIDE.md` for step-by-step instructions

3. **Test your configuration**:
   ```bash
   python test_keys.py
   ```

4. **Run the Streamlit app**:
   ```bash
   streamlit run app.py
   ```

## 🔑 API Keys Setup

**You need 3 things:**
1. **GOOGLE_API_KEY** - Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **GOOGLE_CLOUD_PROJECT** - Your project ID from Google Cloud Console
3. **GOOGLE_APPLICATION_CREDENTIALS** - Service account JSON file

📖 **Detailed instructions**: See `API_KEYS_GUIDE.md` for complete setup guide.

## 📁 Project Structure

```
hack/
├── agents/           # Agent implementations
├── handlers/         # Input handlers (YouTube, Live)
├── utils/             # Helper functions
├── app.py            # Streamlit frontend
├── pipeline.py       # Main orchestrator
└── requirements.txt
```

## 🔧 Configuration

Set up your Google Cloud project and enable:
- Video Intelligence API
- Vertex AI
- Generative AI APIs (Gemini, Veo, Imagen)

