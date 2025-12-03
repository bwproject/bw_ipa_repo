import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from bot.handlers import register_handlers

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем хэндлеры
register_handlers(dp)

async def start_bot():
    logging.info("Запуск Telegram бота...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()