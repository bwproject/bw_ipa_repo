from telegram.ext import Application
import os
from dotenv import load_dotenv
from bot.handlers import register_handlers

load_dotenv()

async def start_bot():
    app = Application.builder().token(os.getenv("BOT_TOKEN")).build()

    # регистрация всех хендлеров
    register_handlers(app)

    # правильный запуск polling в python-telegram-bot v20+
    await app.run_polling()