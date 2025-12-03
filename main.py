import asyncio
import logging
from bot.bot import start_bot
from server.server import start_server

# -----------------------------
# Настройка логов
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[\033[92m%(asctime)s\033[0m] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("ipa_repo")


async def main():
    logger.info("🚀 Запуск IPA-репозитория начинается...")

    try:
        logger.info("🌐 Запускаю веб-сервер...")
        server_task = asyncio.create_task(start_server())
    except Exception as e:
        logger.error(f"❌ Ошибка запуска сервера: {e}")
        return

    try:
        logger.info("🤖 Запускаю Telegram-бота...")
        bot_task = asyncio.create_task(start_bot())
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        return

    logger.info("✅ Все компоненты запущены. Работаем...")

    await asyncio.gather(server_task, bot_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("🛑 Остановка по Ctrl+C…")
    except Exception as e:
        logger.error(f"🔥 Критическая ошибка: {e}")