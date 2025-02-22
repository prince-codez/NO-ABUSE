import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import requests
import openai
import os

# ✅ Load Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID"))
API_USER = os.getenv("SIGHTENGINE_API_USER")
API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")
NSFW_API_URL = "https://api.sightengine.com/1.0/check.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Dictionary to track user violations
violations = {}

# ✅ Function to check if an image/video is NSFW
def is_nsfw(file_path):
    with open(file_path, "rb") as f:
        response = requests.post(NSFW_API_URL, files={"media": f}, data={
            "models": "nudity",
            "api_user": API_USER,
            "api_secret": API_SECRET
        })
    result = response.json()
    return result.get("nudity", {}).get("safe", 1) < 0.7

# ✅ Function to check text for NSFW content
def is_nsfw_text(text):
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Detect if this message contains 18+ content."},
                  {"role": "user", "content": text}]
    )
    return "yes" in response['choices'][0]['message']['content'].lower()

# ✅ /start command function
def start(update, context):
    user_name = update.message.from_user.first_name
    update.message.reply_text(f"👋 **Welcome, {user_name}!**\n\nThis bot automatically removes NSFW content from chats.")

# ✅ /check command function (API status check)
def check(update, context):
    error_logs = []

    # ✅ Check SightEngine API
    try:
        test_response = requests.get(NSFW_API_URL, params={
            "models": "nudity",
            "api_user": API_USER,
            "api_secret": API_SECRET
        })
        if test_response.status_code != 200:
            error_logs.append("❌ SightEngine API Error: " + test_response.text)
    except Exception as e:
        error_logs.append(f"❌ SightEngine API Exception: {str(e)}")

    # ✅ Check OpenAI API
    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test message"}]
        )
    except Exception as e:
        error_logs.append(f"❌ OpenAI API Exception: {str(e)}")

    # ✅ Send status message
    if error_logs:
        update.message.reply_text("\n".join(error_logs))
    else:
        update.message.reply_text("✅ All APIs are working correctly!")

# ✅ Function to handle messages
def handle_messages(update, context):
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.username or message.from_user.first_name

    # Check for NSFW text
    if message.text and is_nsfw_text(message.text):
        message.delete()
        context.bot.send_message(chat_id, f"⚠️ **NSFW text detected!**\nMessage deleted.")
        log_violation(user_id, user_name, chat_id, context)

    # Check for NSFW images/videos
    elif message.photo or message.video:
        file = message.photo[-1].get_file() if message.photo else message.video.get_file()
        file_path = file.download()

        if is_nsfw(file_path):
            message.delete()
            context.bot.send_message(chat_id, f"⚠️ **NSFW media detected!**\nMessage deleted.")
            log_violation(user_id, user_name, chat_id, context)

# ✅ Function to log user violations
def log_violation(user_id, user_name, chat_id, context):
    if user_id not in violations:
        violations[user_id] = 1
    else:
        violations[user_id] += 1

    # Warn User
    if violations[user_id] == 1:
        context.bot.send_message(chat_id, f"⚠️ **Warning:** {user_name}, sending NSFW content is not allowed!")
    # Ban User after 3 violations
    elif violations[user_id] >= 3:
        context.bot.kick_chat_member(chat_id, user_id)
        context.bot.send_message(chat_id, f"🚫 {user_name} has been banned for sending NSFW content!")

    # Log to Admin
    context.bot.send_message(ADMIN_CHAT_ID, f"🚨 **Violation Alert** 🚨\n👤 User: {user_name}\n⚠️ Warnings: {violations[user_id]}")

# ✅ Main function
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("check", check))
    
    # Add message handler
    dp.add_handler(MessageHandler(Filters.text | Filters.photo | Filters.video, handle_messages))

    # Start bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()