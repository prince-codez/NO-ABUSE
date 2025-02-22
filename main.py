import os
import requests
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

# ✅ Environment Variables
TOKEN = os.getenv("BOT_TOKEN")  # Bot Token
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))  # Admin Telegram ID
API_USER = os.getenv("SIGHTENGINE_API_USER")  # SightEngine API User
API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")  # SightEngine API Secret
NSFW_API_URL = "https://api.sightengine.com/1.0/check.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API Key

# ✅ Warnings Dictionary
violations = {}

# ✅ NSFW Image/Video Detection (SightEngine)
async def is_nsfw(file_path):
    try:
        with open(file_path, "rb") as f:
            response = requests.post(NSFW_API_URL, files={"media": f}, data={
                "models": "nudity,wad,offensive",
                "api_user": API_USER,
                "api_secret": API_SECRET
            })
        result = response.json()
        return result.get("nudity", {}).get("safe", 1) < 0.7  # If "safe" < 0.7, it's NSFW
    except Exception as e:
        print(f"❌ NSFW API Error: {e}")
        return False

# ✅ NSFW Text Detection (OpenAI)
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
        print(f"❌ OpenAI API Error: {e}")
        return False

# ✅ /start Command
async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(f"👋 **Welcome, {user_name}!**\n\nThis bot removes NSFW content from the group.")

# ✅ Message Handler
async def handle_messages(update: Update, context: CallbackContext):
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.username or message.from_user.first_name

    # ✅ NSFW Text Detection
    if message.text and await is_nsfw_text(message.text):
        await message.delete()
        await context.bot.send_message(chat_id, f"⚠️ **NSFW text detected!** Message deleted.")
        await log_violation(user_id, user_name, chat_id, context)
        return

    # ✅ NSFW Media Detection (Images, Videos, GIFs)
    file = None
    if message.photo:
        file = await message.photo[-1].get_file()
    elif message.video:
        file = await message.video.get_file()
    elif message.animation:  # GIFs
        file = await message.animation.get_file()

    if file:
        file_path = await file.download()
        if await is_nsfw(file_path):
            await message.delete()
            await context.bot.send_message(chat_id, f"⚠️ **NSFW media detected!** Message deleted.")
            await log_violation(user_id, user_name, chat_id, context)
            return

# ✅ Log Violation & Ban System
async def log_violation(user_id, user_name, chat_id, context):
    if user_id not in violations:
        violations[user_id] = 1
    else:
        violations[user_id] += 1

    # ✅ Warn User
    if violations[user_id] <= 4:
        await context.bot.send_message(chat_id, f"⚠️ **Warning {violations[user_id]}/5:** {user_name}, NSFW content is not allowed!")
    # 🚫 Ban User after 5 Violations
    elif violations[user_id] >= 5:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.send_message(chat_id, f"🚫 {user_name} has been banned for sending NSFW content!")

    # ✅ Notify Admin
    await context.bot.send_message(ADMIN_CHAT_ID, f"🚨 **Violation Alert** 🚨\n👤 User: {user_name}\n⚠️ Warnings: {violations[user_id]}")

# ✅ Main Bot Function
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # ✅ Commands
    app.add_handler(CommandHandler("start", start))

    # ✅ Message Handling
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION, handle_messages))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
