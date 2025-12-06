# main.py (https://github.com/bwproject/bw_ipa_repo/blob/main/main.py)

#!/usr/bin/env python3

import asyncio
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("bw_ipa_repo")

# ======== Папки ========
BASE = Path("repo")                   # корневая папка репозитория
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
INDEX_HTML = Path("index/template.html")

BASE.mkdir(parents=True, exist_ok=True)
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# ======== FastAPI ========
app = FastAPI(title="bw_ipa_repo")

# ===============================
#          РУТ /
# ===============================
@app.get("/", response_class=FileResponse)
async def root_index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return FileResponse("index_not_found.html")

# ===============================
#         /repo/index.json
# ===============================
@app.get("/repo/index.json")
async def get_index():
    index_file = BASE / "index.json"
    if index_file.exists():
        logger.info("Serving index.json")
        return FileResponse(index_file)
    logger.warning("index.json NOT FOUND")
    return {"error": "index.json not found"}, 404


# ===============================
#        IPA пакеты
# ===============================
@app.get("/repo/packages/{file_name}")
async def get_package(file_name: str):
    path = PACKAGES / file_name
    if path.exists():
        logger.info(f"Serving package {file_name}")
        return FileResponse(path)
    logger.warning(f"Package not found: {file_name}")
    return {"error": "file not found"}, 404


# ===============================
#             картинки
# ===============================
@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    path = IMAGES / file_name
    if path.exists():
        logger.info(f"Serving image {file_name}")
        return FileResponse(path)
    logger.warning(f"Image not found: {file_name}")
    return {"error": "file not found"}, 404


# ===============================
#      Загрузка IPA через API
# ===============================
@app.post("/upload")
async def upload_ipa(file: UploadFile = File(...)):
    filename = file.filename
    target = PACKAGES / filename

    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    logger.info(f"Uploaded IPA → {filename}")
    return {"status": "ok", "saved": filename}


# ===============================
#   Подключение статической /webapp
# ===============================
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")


# ===============================
#     Запуск FastAPI и Telegram
# ===============================
from bot.bot import start_bot  # импорт после объявления app


async def start_services():
    import uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info"
    )
    server = uvicorn.Server(config)

    logger.info("Starting FastAPI + Telegram bot...")
    await asyncio.gather(
        server.serve(),
        start_bot()
    )


if __name__ == "__main__":
    logger.info("Starting main.py")
    asyncio.run(start_services())