# main.py (https://github.com/bwproject/bw_ipa_repo/blob/main/main.py)

#!/usr/bin/env python3

import asyncio
import os
import logging
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("bw_ipa_repo")

# ======== Paths ========
BASE = Path("repo")          # локальная папка repo
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
INDEX_HTML = Path("index/template.html")  # Статический HTML шаблон

BASE.mkdir(parents=True, exist_ok=True)
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# ======== FastAPI app ========
app = FastAPI(title="bw_ipa_repo")

# ======== Корневой маршрут / ========
@app.get("/", response_class=FileResponse)
async def root_index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return FileResponse("index_not_found.html")  # альтернативный файл с сообщением

# ======== API: получить index.json ========
@app.get("/repo/index.json")
async def get_index():
    p = BASE / "index.json"
    if p.exists():
        logger.info("Serving index.json")
        return FileResponse(p)
    logger.warning("index.json not found")
    return JSONResponse({"error": "index.json not found"}, status_code=404)

# ======== API: получение IPA файлов ========
@app.get("/repo/packages/{file_name}")
async def get_package(file_name: str):
    p = PACKAGES / file_name
    if p.exists():
        logger.info(f"Serving package {file_name}")
        return FileResponse(p)
    logger.warning(f"Package not found: {file_name}")
    return JSONResponse({"error": "file not found"}, status_code=404)

# ======== API: получение картинок ========
@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    p = IMAGES / file_name
    if p.exists():
        logger.info(f"Serving image {file_name}")
        return FileResponse(p)
    logger.warning(f"Image not found: {file_name}")
    return JSONResponse({"error": "file not found"}, status_code=404)

# ======== Загрузка IPA через FastAPI ========
@app.post("/upload")
async def upload_ipa(file: UploadFile = File(...)):
    filename = file.filename
    target = PACKAGES / filename

    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    logger.info(f"Uploaded {filename}")
    return {"status": "ok", "saved": filename}

# ======== Статика /webapp ========
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")

# ======== Запуск Telegram бота и FastAPI ========
from bot.bot import start_bot  # локальный импорт, чтобы избежать circular import

async def start_services():
    import uvicorn
    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))
    cfg = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(cfg)
    logger.info("Starting FastAPI + Telegram bot...")
    await asyncio.gather(server.serve(), start_bot())

if __name__ == "__main__":
    logger.info("Starting main.py")
    asyncio.run(start_services())