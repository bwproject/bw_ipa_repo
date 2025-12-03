import asyncio
import logging
from bot.bot import start_bot
from server.server import start_server

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("ipa_repo")


async def main():
    logger.info("🚀 Запуск системы...")

    server_task = asyncio.create_task(start_server())
    bot_task = asyncio.create_task(start_bot())

    await asyncio.gather(server_task, bot_task)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # ← сюда попадём если уже есть активный event loop
        logger.warning("⚠ Event loop уже запущен, переключаюсь на альтернативный запуск...")

        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()