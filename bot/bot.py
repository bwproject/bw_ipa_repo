from telegram.ext import Application
import os
from dotenv import load_dotenv
from bot.handlers import register_handlers

load_dotenv()

async def start_bot():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
    register_handlers(app)
    await app.run_polling()