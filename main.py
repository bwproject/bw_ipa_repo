# main.py (https://github.com/bwproject/bw_ipa_repo/blob/main/main.py)

#!/usr/bin/env python3

import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Request
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
BASE = Path("repo")                 # локальная папка repo
PACKAGES = BASE / "packages"        # JSON + IPA
IMAGES = BASE / "images"            # изображения
INDEX_HTML = Path("index/template.html")  # Статический HTML шаблон

BASE.mkdir(parents=True, exist_ok=True)
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# ======== FastAPI app ========
app = FastAPI(title="bw_ipa_repo")

# ======== Функция проверки доступа ========
def check_access(tgid: int) -> bool:
    allowed = os.getenv("ALLOWED_IDS", "")
    if not allowed:
        return False
    return str(tgid) in allowed.split(",")

# ======== Корневой маршрут / ========
@app.get("/", response_class=FileResponse)
async def root_index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return JSONResponse({"error": "index template not found"}, status_code=404)

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

# ======== Загрузка IPA ========
@app.post("/upload")
async def upload_ipa(file: UploadFile = File(...)):
    filename = file.filename
    target = PACKAGES / filename

    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    logger.info(f"Uploaded {filename}")
    return {"status": "ok", "saved": filename}

# ==========================================================
#       API ДЛЯ WEBAPP: /api/app/get и /api/app/update
# ==========================================================

# ==== GET: получить данные JSON ====
@app.get("/api/app/get")
async def api_get_app(app: str, tgid: int):

    if not check_access(int(tgid)):
        return JSONResponse({"ok": False, "error": "Access denied"})

    file = PACKAGES / f"{app}.json"
    if not file.exists():
        return JSONResponse({"ok": False, "error": "JSON not found"})

    data = json.loads(file.read_text("utf-8"))

    return JSONResponse({
        "ok": True,
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "bundle": data.get("bundleIdentifier", ""),
        "version": data.get("versions", [{}])[0].get("version", "")
    })

# ==== POST: обновление JSON ====
@app.post("/api/app/update")
async def api_update_app(request: Request):

    body = await request.json()

    app_name = body.get("app")
    tgid = body.get("tgid")

    if not app_name or not tgid:
        return JSONResponse({"ok": False, "error": "Missing params"})

    if not check_access(int(tgid)):
        return JSONResponse({"ok": False, "error": "Access denied"})

    file = PACKAGES / f"{app_name}.json"
    if not file.exists():
        return JSONResponse({"ok": False, "error": "JSON not found"})

    data = json.loads(file.read_text("utf-8"))

    # Обновляем поля
    data["name"] = body.get("name", data.get("name"))
    data["description"] = body.get("description", data.get("description"))
    data["bundleIdentifier"] = body.get("bundle", data.get("bundleIdentifier"))

    if "versions" not in data:
        data["versions"] = [{}]

    data["versions"][0]["version"] = body.get(
        "version",
        data["versions"][0].get("version")
    )

    file.write_text(json.dumps(data, indent=4, ensure_ascii=False), "utf-8")

    logger.info(f"Updated {app_name}.json")

    return JSONResponse({"ok": True})

# ==========================================================

# ======== Статика /webapp ========
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")

# ======== Запуск Telegram бота и FastAPI ========
from bot.bot import start_bot  # локальный импорт

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