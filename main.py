import os
import requests
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

# ✅ Load Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))  # Default to 0 if not set
API_USER = os.getenv("SIGHTENGINE_API_USER")
API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")
NSFW_API_URL = "https://api.sightengine.com/1.0/check.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ✅ Dictionary to track user violations
violations = {}

# ✅ Function to check if media is NSFW
async def is_nsfw(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(NSFW_API_URL, files={"media": f}, data={
                "models": "nudity,wad,offensive",
                "api_user": API_USER,
                "api_secret": API_SECRET
            })
        result = response.json()
        return result.get("nudity", {}).get("safe", 1) < 0.7
    except Exception as e:
        print(f"NSFW API Error: {e}")
        return False

# ✅ Function to check text for NSFW content
async def is_nsfw_text(text):
    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Detect if this message contains 18+ content."},
                      {"role": "user", "content": text}]
        )
        return "yes" in response['choices'][0]['message']['content'].lower()
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return False

# ✅ /start command function
async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(f"👋 **Welcome, {user_name}!**\n\nThis bot automatically removes NSFW content from chats.")

# ✅ /check command function (API status check)
async def check(update: Update, context: CallbackContext):
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
        await update.message.reply_text("\n".join(error_logs))
    else:
        await update.message.reply_text("✅ All APIs are working correctly!")

# ✅ Function to handle messages
async def handle_messages(update: Update, context: CallbackContext):
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.username or message.from_user.first_name

    # ✅ NSFW Text Detection
    if message.text and await is_nsfw_text(message.text):
        await message.delete()
        await context.bot.send_message(chat_id, f"⚠️ **NSFW text detected!**\nMessage deleted.")
        await log_violation(user_id, user_name, chat_id, context)
        return

    # ✅ NSFW Media Detection (Images, Videos, GIFs, Stickers)
    file = None
    if message.photo:
        file = await message.photo[-1].get_file()
    elif message.video:
        file = await message.video.get_file()
    elif message.animation:  # GIFs
        file = await message.animation.get_file()
    elif message.sticker and message.sticker.is_animated is False:  # Static Stickers
        file = await message.sticker.get_file()

    if file:
        file_path = await file.download()
        if await is_nsfw(file_path):
            await message.delete()
            await context.bot.send_message(chat_id, f"⚠️ **NSFW media detected!**\nMessage deleted.")
            await log_violation(user_id, user_name, chat_id, context)
            return

    # ✅ Ignore audio files (NSFW detection not possible)
    if message.audio or message.voice:
        return    

# ✅ Function to log user violations
async def log_violation(user_id, user_name, chat_id, context):
    if user_id not in violations:
        violations[user_id] = 1
    else:
        violations[user_id] += 1

    # Warn User
    if violations[user_id] == 1:
        await context.bot.send_message(chat_id, f"⚠️ **Warning:** {user_name}, sending NSFW content is not allowed!")
    # Ban User after 3 violations
    elif violations[user_id] >= 3:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.send_message(chat_id, f"🚫 {user_name} has been banned for sending NSFW content!")

    # Log to Admin
    await context.bot.send_message(ADMIN_CHAT_ID, f"🚨 **Violation Alert** 🚨\n👤 User: {user_name}\n⚠️ Warnings: {violations[user_id]}")

# ✅ Main function
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check))
      
    # Add message handler
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.STICKER, handle_messages))

    # Start bot
    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
