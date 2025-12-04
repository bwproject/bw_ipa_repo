import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not set in env")

logging.getLogger("aiogram").setLevel(logging.INFO)
logger = logging.getLogger("bot")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# register handlers (local import)
from bot.handlers import register_handlers
register_handlers(dp)

async def start_bot():
    logger.info("Starting Telegram bot (polling)...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()