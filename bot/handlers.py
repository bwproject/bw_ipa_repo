# main.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import os
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from bot.handlers import register_handlers
from bot.access import check_access

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# ==============================
# ФАЙЛОВЫЕ ПУТИ
# ==============================
BASE_DIR = Path(__file__).parent
REPO_DIR = BASE_DIR / "repo"
WEBAPP_DIR = BASE_DIR / "webapp"

# ==============================
# STATIC ROUTES
# ==============================
async def serve_root(request):
    """
    / → /index/template.html
    """
    redirect_path = "/index/template.html"
    raise web.HTTPFound(redirect_path)

async def serve_index_template(request):
    file_path = BASE_DIR / "index" / "template.html"
    return web.FileResponse(path=file_path)

async def serve_webapp_file(request):
    """
    Отдача файлов из /webapp
    """
    filename = request.match_info.get("filename")
    file_path = WEBAPP_DIR / filename

    if not file_path.exists():
        raise web.HTTPNotFound()

    return web.FileResponse(path=file_path)

async def serve_static(request):
    """
    Отдача любых файлов /repo/*
    """
    rel_path = request.match_info.get("path")
    file_path = BASE_DIR / "repo" / rel_path

    if not file_path.exists():
        raise web.HTTPNotFound()

    return web.FileResponse(path=file_path)

# ==============================
# API: обновление metadata JSON
# ==============================
async def api_update_app(request):
    """
    POST /api/app/update
    """
    data = await request.json()
    app = data.get("app")
    tgid = int(data.get("tgid", 0))

    if not check_access(tgid):
        return web.json_response({"error": "access denied"}, status=403)

    if not app:
        return web.json_response({"error": "no app"}, status=400)

    json_path = REPO_DIR / "packages" / f"{app}.json"
    if not json_path.exists():
        return web.json_response({"error": "meta not found"}, status=404)

    # обновляем поля
    meta = json.loads(json_path.read_text(encoding="utf-8"))

    for key in ["name", "bundleIdentifier", "localizedDescription", "version"]:
        if key in data:
            if key == "version":
                meta["versions"][0]["version"] = data["version"]
            else:
                meta[key] = data[key]

    # пересохраняем
    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=4),
        encoding="utf-8"
    )

    return web.json_response({"status": "ok"})

# ==============================
# Telegram bot
# ==============================
async def start_bot():
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in .env")

    bot = Bot(TOKEN, parse_mode="HTML")
    dp = Dispatcher()
    register_handlers(dp)

    await dp.start_polling(bot)

# ==============================
# MAIN запускает и БОТ и WEB
# ==============================
def build_web_app():
    app = web.Application()

    # root → template
    app.router.add_get("/", serve_root)

    # index
    app.router.add_get("/index/template.html", serve_index_template)

    # webapp
    app.router.add_get("/webapp/{filename}", serve_webapp_file)

    # API
    app.router.add_post("/api/app/update", api_update_app)

    # static repo
    app.router.add_get("/repo/{path:.*}", serve_static)

    return app


async def main():
    app = build_web_app()

    web_task = asyncio.create_task(
        web._run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
    )
    bot_task = asyncio.create_task(start_bot())

    await asyncio.gather(web_task, bot_task)


if __name__ == "__main__":
    asyncio.run(main())