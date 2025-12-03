import asyncio
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

# -----------------------------
# Telegram
# -----------------------------
from bot.bot import start_bot

# -----------------------------
# Load .env
# -----------------------------
load_dotenv()

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
        return FileResponse(path)
    return {"error": "File not found"}


@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    path = IMAGES / file_name
    if path.exists():
        return FileResponse(path)
    return {"error": "File not found"}


# -----------------------------
# Параллельный запуск сервера и бота
# -----------------------------
async def main():
    # Запуск FastAPI сервера
    import uvicorn
    server = uvicorn.Server(
        uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    )

    # Запуск сервера и бота параллельно
    await asyncio.gather(
        server.serve(),
        start_bot()
    )


if __name__ == "__main__":
    asyncio.run(main())