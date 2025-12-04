# main.py (https://github.com/bwproject/bw_ipa_repo/blob/main/main.py)

#!/usr/bin/env python3

import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger("bw_ipa_repo")

# Paths
BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
INDEX_HTML = Path("index/template.html")  # Шаблон HTML для корня

BASE.mkdir(parents=True, exist_ok=True)
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# FastAPI app
app = FastAPI(title="bw_ipa_repo")

# ======== Корневой маршрут / ========
@app.get("/", response_class=HTMLResponse)
async def root_index():
    index_file = BASE / "index.json"
    if not index_file.exists():
        return HTMLResponse("<h1>index.json not found</h1>", status_code=404)

    try:
        with open(index_file, "r", encoding="utf-8") as f:
            apps = json.load(f)
            if not isinstance(apps, list):
                raise ValueError("index.json should contain a list")
    except Exception as e:
        logger.exception("Error reading index.json")
        return HTMLResponse(f"<h1>Failed to read index.json</h1><pre>{e}</pre>", status_code=500)

    if not INDEX_HTML.exists():
        return HTMLResponse("<h1>HTML template not found</h1>", status_code=500)

    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html_template = f.read()

    apps_html = ""
    for app_item in apps:
        name = app_item.get("name", "Unnamed")
        version = app_item.get("version", "N/A")
        bundle = app_item.get("bundleIdentifier", "")
        file_name = app_item.get("file_name", "")
        icon_name = app_item.get("icon", "")

        ipa_link = f"/repo/packages/{file_name}" if file_name else "#"
        img_link = f"/repo/images/{icon_name}" if icon_name else "https://via.placeholder.com/128"

        apps_html += f'''
        <div class="app-card">
            <img src="{img_link}" alt="{name}">
            <div class="app-info">
                <div class="app-name">{name}</div>
                <div class="app-bundle">{bundle}</div>
                <div class="app-version">{version}</div>
                <a href="{ipa_link}" class="download-btn">Download</a>
            </div>
        </div>
        '''

    html_content = html_template.replace("{{APPS_LIST}}", apps_html)
    return HTMLResponse(content=html_content, status_code=200)

# ======== Существующие маршруты /repo ========
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
        logger.info(f"Serving package {file_name}")
        return FileResponse(p)
    logger.warning(f"Package not found: {file_name}")
    return {"error": "file not found"}, 404

@app.get("/repo/images/{file_name}")
async def get_image(file_name: str):
    p = IMAGES / file_name
    if p.exists():
        logger.info(f"Serving image {file_name}")
        return FileResponse(p)
    logger.warning(f"Image not found: {file_name}")
    return {"error": "file not found"}, 404

@app.post("/upload")
async def upload_ipa(file: UploadFile = File(...)):
    filename = file.filename
    target = PACKAGES / filename

    with open(target, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    return {"status": "ok", "saved": filename}

app.mount("/webapp", StaticFiles(directory="webapp"), name="webapp")

# import bot start after app defined to avoid circular imports
from bot.bot import start_bot  # local import

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