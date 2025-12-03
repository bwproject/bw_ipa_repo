import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from bot.handlers import register_handlers

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Регистрация хэндлеров
register_handlers(dp)

@dp.message(Command(commands=["start"]))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот IPA репозитория.\n"
        "Отправляй IPA файлы и используй /repo для обновления index.json."
    )

async def start_bot():
    logging.info("Запуск Telegram бота...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()