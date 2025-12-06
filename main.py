# main.py (https://github.com/bwproject/bw_ipa_repo/blob/main/main.py)

#!/usr/bin/env python3

import asyncio
import os
import logging
import json
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("bw_ipa_repo")

# ==============================
# Папки
# ==============================
BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
INDEX_HTML = Path("webapp/update.html")  # Статический HTML для редактирования

BASE.mkdir(parents=True, exist_ok=True)
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# ==============================
# FastAPI
# ==============================
app = FastAPI(title="bw_ipa_repo")

# ==============================
# API: получить приложение
# ==============================
@app.get("/api/app/get")
async def api_get_app(app: str, tgid: int):
    users_file = BASE / "users.json"
    if users_file.exists():
        users = json.loads(users_file.read_text(encoding="utf-8"))
    else:
        users = []

    if tgid not in users:
        return {"ok": False, "error": "Нет доступа"}

    json_file = PACKAGES / f"{app}.json"
    if not json_file.exists():
        return {"ok": False, "error": "Приложение не найдено"}

    data = json.loads(json_file.read_text(encoding="utf-8"))

    return {
        "ok": True,
        "name": data.get("name", ""),
        "description": data.get("localizedDescription", ""),
        "bundle": data.get("bundleIdentifier", ""),
        "version": data.get("versions", [{}])[0].get("version", "1.0")
    }

# ==============================
# Модель для обновления
# ==============================
class AppUpdate(BaseModel):
    app: str
    tgid: int
    name: str
    description: str
    bundle: str
    version: str

# ==============================
# API: обновить приложение
# ==============================
@app.post("/api/app/update")
async def api_update_app(data: AppUpdate):
    users_file = BASE / "users.json"
    if users_file.exists():
        users = json.loads(users_file.read_text(encoding="utf-8"))
    else:
        users = []

    if data.tgid not in users:
        return {"ok": False, "error": "Нет доступа"}

    json_file = PACKAGES / f"{data.app}.json"
    if not json_file.exists():
        return {"ok": False, "error": "Приложение не найдено"}

    app_data = json.loads(json_file.read_text(encoding="utf-8"))

    app_data["name"] = data.name
    app_data["localizedDescription"] = data.description
    app_data["bundleIdentifier"] = data.bundle
    if "versions" not in app_data or not app_data["versions"]:
        app_data["versions"] = [{}]
    app_data["versions"][0]["version"] = data.version

    json_file.write_text(json.dumps(app_data, indent=4, ensure_ascii=False), encoding="utf-8")

    return {"ok": True}

# ==============================
# Корень / — отдаём update.html или альтернативный файл
# ==============================
@app.get("/", response_class=FileResponse)
async def root_index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return FileResponse("index_not_found.html")  # альтернативный файл с сообщением

# ==============================
# Раздача index.json
# ==============================
@app.get("/repo/index.json")
async def get_index():
    p = BASE / "index.json"
    if p.exists():
        logger.info("Serving index.json")
        return FileResponse(p)
    logger.warning("index.json not found")
    return {"error": "index.json not found"}, 404

# ==============================
# Раздача IPA
# ==============================
@app.get("/repo/packages/{file_name}")
async def get_package(file_name: str):
    p = PACKAGES / file_name
    if p.exists():
        logger.info(f"Serving package {file_name}")
        return FileResponse(p)
    logger.warning(f"Package not found: {file_name}")
    return {"error": "file not found"}, 404

# ==============================
# Раздача изображений
# ==============================
@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    p = IMAGES / file_name
    if p.exists():
        logger.info(f"Serving image {file_name}")
        return FileResponse(p)
    logger.warning(f"Image not found: {file_name}")
    return {"error": "file not found"}, 404

# ==============================
# Загрузка IPA через API
# ==============================
@app.post("/upload")
async def upload_ipa(file: UploadFile = File(...)):
    filename = file.filename
    target = PACKAGES / filename

    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    return {"status": "ok", "saved": filename}

# ==============================
# Статика для WebApp
# ==============================
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")

# ==============================
# Запуск Telegram бота + FastAPI
# ==============================
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