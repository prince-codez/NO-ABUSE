import os
import requests
import openai
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("BOT_TOKEN")  # Bot Token
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))  # Admin Telegram ID
API_USER = os.getenv("SIGHTENGINE_API_USER")  # SightEngine API User
API_SECRET = os.getenv("SIGHTENGINE_API_SECRET")  # SightEngine API Secret
NSFW_API_URL = "https://api.sightengine.com/1.0/check.json"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API Key

violations = {}

async def start(update: Update, context: CallbackContext):
    user_name = update.message.from_user.first_name
    await update.message.reply_text(f"👋 **Welcome, {user_name}!**\n\nThis bot removes NSFW content from the group.")

async def handle_messages(update: Update, context: CallbackContext):
    message = update.message
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.username or message.from_user.first_name

    if message.text and "18+" in message.text:  # Simple NSFW detection (replace with OpenAI if needed)
        await message.delete()
        await context.bot.send_message(chat_id, f"⚠️ **NSFW text detected!** Message deleted.")
        await log_violation(user_id, user_name, chat_id, context)

async def log_violation(user_id, user_name, chat_id, context):
    violations[user_id] = violations.get(user_id, 0) + 1

    if violations[user_id] <= 4:
        await context.bot.send_message(chat_id, f"⚠️ **Warning {violations[user_id]}/5:** {user_name}, NSFW content is not allowed!")
    elif violations[user_id] >= 5:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.send_message(chat_id, f"🚫 {user_name} has been banned for sending NSFW content!")

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION, handle_messages))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
