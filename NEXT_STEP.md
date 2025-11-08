# 🎯 Next Step: Create Service Account Key

You've created the service account, but you still need to **download the JSON key file**.

## ✅ What You Have:
- ✅ Project ID: `game-watcher-ai`
- ✅ API Key: `AIzaSyD79kU8NACy4flBug-nTNLsevmBt6KzDdE`
- ✅ Service Account: `game-watcher-ai@game-watcher-ai.iam.gserviceaccount.com`

## ⚠️ What's Missing:
- ❌ JSON Key File (Key ID shows "No keys")

## 📥 How to Create the JSON Key:

1. **In the Google Cloud Console**, click on the service account email:
   `game-watcher-ai@game-watcher-ai.iam.gserviceaccount.com`
   (The blue link in the Email column)

2. **Go to the "Keys" tab** (at the top of the page)

3. **Click "Add Key"** → **"Create new key"**

4. **Select "JSON"** format

5. **Click "Create"** - This will download a JSON file

6. **Save the file** as `service-account-key.json` in your project folder:
   `/Users/devpatel/hack/service-account-key.json`

## 📝 Then Create Your `.env` File:

Create a file named `.env` in `/Users/devpatel/hack/` with this content:

```bash
GOOGLE_CLOUD_PROJECT=game-watcher-ai
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GOOGLE_API_KEY=AIzaSyD79kU8NACy4flBug-nTNLsevmBt6KzDdE
```

## ✅ Test It:

After creating the `.env` file and downloading the JSON key, run:

```bash
python test_keys.py
```

This will verify everything is set up correctly!

