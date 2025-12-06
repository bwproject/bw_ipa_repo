# main.py (https://github.com/bwproject/bw_ipa_repo/blob/main/main.py)

#!/usr/bin/env python3

import asyncio
import os
import logging
import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# ==========================
#   INITIAL SETUP
# ==========================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("bw_ipa_repo")

BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"

INDEX_HTML = Path("index/template.html")

BASE.mkdir(parents=True, exist_ok=True)
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# ==========================
#   FASTAPI APP
# ==========================

app = FastAPI(title="bw_ipa_repo")

# ---------- ROOT ----------
@app.get("/", response_class=FileResponse)
async def root_index():
    if INDEX_HTML.exists():
        return FileResponse(INDEX_HTML)
    return FileResponse("index_not_found.html")


# ==========================
#   REPO FILE ROUTES
# ==========================

@app.get("/repo/index.json")
async def get_index():
    p = BASE / "index.json"
    if p.exists():
        logger.info("Serving index.json")
        return FileResponse(p)
    logger.warning("index.json not found")
    return {"error": "index.json not found"}, 404


@app.get("/repo/packages/{file_name}")
async def get_package(file_name: str):
    p = PACKAGES / file_name
    if p.exists():
        logger.info(f"Serving package: {file_name}")
        return FileResponse(p)
    return {"error": "file not found"}, 404


@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    p = IMAGES / file_name
    if p.exists():
        logger.info(f"Serving image: {file_name}")
        return FileResponse(p)
    return {"error": "file not found"}, 404


# ==========================
#   UPLOAD IPA
# ==========================

@app.post("/upload")
async def upload_ipa(file: UploadFile = File(...)):
    filename = file.filename
    target = PACKAGES / filename

    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    logger.info(f"IPA uploaded: {filename}")
    return {"status": "ok", "saved": filename}


# ==========================
#   STATIC WEBAPP
# ==========================

app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")


# ==========================
#   API: UPDATE APP META
# ==========================

@app.post("/api/app/update")
async def api_app_update(
    tgid: int = Form(...),
    app_id: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    version: str = Form(...),
    bundleid: str = Form(...)
):
    index_file = BASE / "index.json"

    if not index_file.exists():
        raise HTTPException(404, "index.json not found")

    # Проверка доступа через allowed_users.txt
    allowed_path = Path("allowed_users.txt")
    if not allowed_path.exists():
        raise HTTPException(403, "allowed_users.txt not found")

    allowed = allowed_path.read_text().strip().splitlines()

    if str(tgid) not in allowed:
        raise HTTPException(403, "Access denied")

    # Загружаем index.json
    with open(index_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    app_found = None
    for app in data.get("apps", []):
        if app.get("id") == app_id or app.get("bundleid") == bundleid:
            app_found = app
            break

    if not app_found:
        raise HTTPException(404, "App not found")

    # Обновление полей
    app_found["title"] = title
    app_found["description"] = description
    app_found["version"] = version
    app_found["bundleid"] = bundleid

    # Сохраняем
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info(f"UPDATED [{app_id}] {title}")
    return {"status": "ok", "updated": app_id}


# ==========================
#   RUN BOT + FASTAPI
# ==========================

from bot.bot import start_bot  # избегаем circular import

async def start_services():
    import uvicorn

    host = "0.0.0.0"
    port = int(os.getenv("PORT", 8000))

    cfg = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(cfg)

    logger.info("Starting FastAPI + Telegram bot...")

    await asyncio.gather(
        server.serve(),
        start_bot()
    )


if __name__ == "__main__":
    logger.info("Starting main.py")
    asyncio.run(start_services())