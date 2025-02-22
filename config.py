import os

# ✅ Load environment variables from Heroku
API_ID = int(os.getenv("API_ID"))  # Convert to integer
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))  # Convert to integer

# ✅ SightEngine API (For NSFW Detection)
SIGHTENGINE_API_USER = os.getenv("SIGHTENGINE_API_USER")
SIGHTENGINE_API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")
NSFW_API_URL = "https://api.sightengine.com/1.0/check.json"

# ✅ OpenAI API Key (For NSFW Text Detection)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")