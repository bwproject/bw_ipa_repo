import asyncio
import os
import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from bot.bot import start_bot

# -----------------------------
# Load .env
# -----------------------------
load_dotenv()

# -----------------------------
# Настройка логирования
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# -----------------------------
# Папки репозитория
# -----------------------------
BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# -----------------------------
# FastAPI сервер
# -----------------------------
app = FastAPI()


@app.get("/repo/packages/{file_name}")
async def get_package(file_name: str):
    path = PACKAGES / file_name
    if path.exists():
        logger.info(f"Отдан файл IPA: {file_name}")
        return FileResponse(path)
    logger.warning(f"Файл IPA не найден: {file_name}")
    return {"error": "File not found"}


@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    path = IMAGES / file_name
    if path.exists():
        logger.info(f"Отдана иконка: {file_name}")
        return FileResponse(path)
    logger.warning(f"Иконка не найдена: {file_name}")
    return {"error": "File not found"}


@app.get("/repo/index.json")
async def get_index():
    path = BASE_PATH / "index.json"
    if path.exists():
        logger.info("Отдан index.json")
        return FileResponse(path)
    logger.warning("index.json не найден")
    return {"error": "index.json не найден"}


# -----------------------------
# Параллельный запуск сервера и бота
# -----------------------------
async def main():
    import uvicorn
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)), log_level="info")
    )

    logger.info("Запуск сервера и бота...")
    try:
        await asyncio.gather(
            server.serve(),
            start_bot()
        )
    except Exception as e:
        logger.exception(f"Ошибка при запуске: {e}")


if __name__ == "__main__":
    logger.info("Старт приложения main.py")
    asyncio.run(main())