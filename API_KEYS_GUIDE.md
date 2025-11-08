# 🔑 API Keys Setup Guide

## ✅ Yes, You Need a `.env` File

The `.env` file stores your API keys and configuration securely. **Never commit this file to git** (it's already in `.gitignore`).

---

## 📋 Required API Keys & Credentials

You need **3 things**:

1. **GOOGLE_API_KEY** - For Gemini, Veo, and Imagen APIs
2. **GOOGLE_CLOUD_PROJECT** - Your Google Cloud project ID
3. **GOOGLE_APPLICATION_CREDENTIALS** - Path to service account JSON file

---

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **"Select a project"** → **"New Project"**
3. Enter project name: `game-watcher-ai` (or any name)
4. Click **"Create"**
5. **Note your Project ID** (shown in the project selector) - you'll need this!
game-watcher-ai
### Step 2: Enable Required APIs

1. In Google Cloud Console, go to **"APIs & Services"** → **"Library"**
2. Search and enable these APIs (click "Enable" for each):
   - **Video Intelligence API** (`videointelligence.googleapis.com`)
   - **Vertex AI API** (`aiplatform.googleapis.com`)
   - **Generative Language API** (`generativelanguage.googleapis.com`)

   Or use the command line:
   ```bash
   gcloud services enable videointelligence.googleapis.com
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable generativelanguage.googleapis.com
   ```

### Step 3: Get Google API Key (for Gemini/Veo/Imagen)

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Or visit: https://aistudio.google.com/app/apikey
2. Click **"Create API Key"**
3. Select your project (the one you created in Step 1)
4. **Copy the API key** - it looks like: `AIzaSy...`
5. ⚠️ **Save this key** - you'll add it to `.env` as `GOOGLE_API_KEY`

**Alternative method:**
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Navigate to **"APIs & Services"** → **"Credentials"**
- Click **"Create Credentials"** → **"API Key"**
- Copy the key
AIzaSyD79kU8NACy4flBug-nTNLsevmBt6KzDdE

### Step 4: Create Service Account (for Video Intelligence API)

The Video Intelligence API requires a service account with credentials.

#### Option A: Using Google Cloud Console (Easier)

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to **"IAM & Admin"** → **"Service Accounts"**
3. Click **"Create Service Account"**
4. Fill in:
   - **Name**: `game-watcher-ai`
   - **Description**: `Service account for Game Watcher AI`
5. Click **"Create and Continue"**
6. Grant roles:
   - **"Vertex AI User"** (`roles/aiplatform.user`)
   - **"Video Intelligence API User"** (if available)
7. Click **"Continue"** → **"Done"**
8. Click on the service account you just created
9. Go to **"Keys"** tab → **"Add Key"** → **"Create new key"**
10. Select **"JSON"** format
11. Click **"Create"** - this downloads a JSON file
12. **Save this file** as `service-account-key.json` in your project root (`/Users/devpatel/hack/`)

#### Option B: Using Command Line

```bash
# Install Google Cloud SDK first: https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login

# Set your project
gcloud config set project YOUR_PROJECT_ID

# Create service account
gcloud iam service-accounts create game-watcher-ai \
    --display-name="Game Watcher AI Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:game-watcher-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Create and download key
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=game-watcher-ai@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

### Step 5: Create `.env` File

1. In your project root (`/Users/devpatel/hack/`), create a file named `.env`
2. Add the following content (replace with your actual values):

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id-here
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GOOGLE_API_KEY=AIzaSy...your-api-key-here

# Video Processing (optional - defaults work fine)
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
TEMP_DIR=temp
```

**Example:**
```bash
GOOGLE_CLOUD_PROJECT=game-watcher-ai-123456
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GOOGLE_API_KEY=AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz1234567
```

---

## ✅ Verification Checklist

- [ ] Google Cloud project created
- [ ] All 3 APIs enabled (Video Intelligence, Vertex AI, Generative Language)
- [ ] Google API key obtained and added to `.env`
- [ ] Service account created
- [ ] Service account JSON file downloaded as `service-account-key.json`
- [ ] `.env` file created with all 3 values filled in
- [ ] `service-account-key.json` is in the project root directory

---

## 🧪 Test Your Setup

Run this quick test to verify everything works:

```python
# test_keys.py
from config import GOOGLE_CLOUD_PROJECT, GOOGLE_API_KEY, GOOGLE_APPLICATION_CREDENTIALS
import os

print("Testing configuration...")
print(f"Project ID: {GOOGLE_CLOUD_PROJECT}")
print(f"API Key: {GOOGLE_API_KEY[:10]}..." if GOOGLE_API_KEY else "❌ Missing")
print(f"Credentials file exists: {os.path.exists(GOOGLE_APPLICATION_CREDENTIALS) if GOOGLE_APPLICATION_CREDENTIALS else '❌ Missing'}")

# Test Gemini API
if GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Say hello")
        print("✅ Gemini API working!")
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
```

Run: `python test_keys.py`

---

## 💰 Free Tier / Costs

- **Gemini API**: Free tier available (check current limits)
- **Video Intelligence API**: Pay-per-use (first 1000 minutes/month may be free)
- **Vertex AI**: Pay-per-use
- **Google Cloud**: $300 free credit for new accounts

**For hackathon**: Free tier should be sufficient for demos!

---

## 🔒 Security Notes

1. **Never commit `.env` or `service-account-key.json` to git**
   - They're already in `.gitignore`
   - Double-check before pushing to GitHub

2. **Restrict API key usage** (optional but recommended):
   - In Google Cloud Console → APIs & Services → Credentials
   - Click on your API key
   - Under "API restrictions", select "Restrict key"
   - Choose: Generative Language API, Video Intelligence API

3. **Service account permissions**:
   - Only grant minimum required permissions
   - Don't use owner/admin roles

---

## 🆘 Troubleshooting

### "API key not valid"
- Check that you copied the full key (no spaces)
- Verify the key is active in Google Cloud Console
- Make sure Generative Language API is enabled

### "Service account credentials not found"
- Verify `service-account-key.json` exists in project root
- Check the path in `.env` is correct (use `./service-account-key.json`)
- Ensure the JSON file is valid (not corrupted)

### "Permission denied" errors
- Verify service account has `roles/aiplatform.user` role
- Check that Video Intelligence API is enabled
- Make sure you're using the correct project ID

### "Quota exceeded"
- Check your Google Cloud billing
- Verify free tier limits
- Some APIs have daily/minute limits

---

## 📞 Quick Reference

| What | Where to Get | Format |
|------|-------------|--------|
| **Project ID** | Google Cloud Console → Project Selector | `my-project-123456` |
| **API Key** | https://aistudio.google.com/app/apikey | `AIzaSy...` |
| **Service Account JSON** | IAM & Admin → Service Accounts → Keys | JSON file download |

---

Need help? Check the main `SETUP.md` or `README.md` files!

