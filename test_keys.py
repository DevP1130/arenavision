"""Quick test script to verify API keys are configured correctly."""
from config import GOOGLE_CLOUD_PROJECT, GOOGLE_API_KEY, GOOGLE_APPLICATION_CREDENTIALS
import os

def test_configuration():
    """Test if all required keys are configured."""
    print("=" * 50)
    print("🔑 Testing API Keys Configuration")
    print("=" * 50)
    print()
    
    # Test Project ID
    print("1. Google Cloud Project ID:")
    if GOOGLE_CLOUD_PROJECT:
        print(f"   ✅ Found: {GOOGLE_CLOUD_PROJECT}")
    else:
        print("   ❌ Missing - Set GOOGLE_CLOUD_PROJECT in .env")
    print()
    
    # Test API Key
    print("2. Google API Key:")
    if GOOGLE_API_KEY:
        print(f"   ✅ Found: {GOOGLE_API_KEY[:15]}...")
    else:
        print("   ❌ Missing - Set GOOGLE_API_KEY in .env")
        print("   Get it from: https://aistudio.google.com/app/apikey")
    print()
    
    # Test Service Account
    print("3. Service Account Credentials:")
    if GOOGLE_APPLICATION_CREDENTIALS:
        if os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
            print(f"   ✅ File exists: {GOOGLE_APPLICATION_CREDENTIALS}")
        else:
            print(f"   ❌ File not found: {GOOGLE_APPLICATION_CREDENTIALS}")
            print("   Download from Google Cloud Console → IAM & Admin → Service Accounts")
    else:
        print("   ❌ Missing - Set GOOGLE_APPLICATION_CREDENTIALS in .env")
    print()
    
    # Test Gemini API
    print("4. Testing Gemini API:")
    if GOOGLE_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content("Say hello in one word")
            print(f"   ✅ Gemini API working! Response: {response.text}")
        except ImportError:
            print("   ⚠️  google-generativeai not installed")
            print("   Run: pip install google-generativeai")
        except Exception as e:
            print(f"   ❌ Gemini API error: {e}")
            print("   Check that your API key is valid and Generative Language API is enabled")
    else:
        print("   ⏭️  Skipped (no API key)")
    print()
    
    # Summary
    print("=" * 50)
    all_good = (
        GOOGLE_CLOUD_PROJECT and 
        GOOGLE_API_KEY and 
        GOOGLE_APPLICATION_CREDENTIALS and 
        os.path.exists(GOOGLE_APPLICATION_CREDENTIALS)
    )
    
    if all_good:
        print("✅ All configuration looks good!")
        print("You're ready to run: streamlit run app.py")
    else:
        print("❌ Some configuration is missing")
        print("See API_KEYS_GUIDE.md for detailed setup instructions")
    print("=" * 50)

if __name__ == "__main__":
    test_configuration()

