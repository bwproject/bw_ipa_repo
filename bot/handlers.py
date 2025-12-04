# bot/handlers.py

import json
import logging
from pathlib import Path
import os

from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.utils import extract_ipa_metadata, get_file_size

logger = logging.getLogger("bot.handlers")

BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Обработка документа (.ipa)
# -----------------------------
async def handle_document(message: types.Message):
    doc = message.document
    if not doc or not doc.file_name.lower().endswith(".ipa"):
        await message.answer("Пожалуйста, отправляйте только файлы .ipa")
        return

    target = PACKAGES / doc.file_name
    await message.answer("🔄 Пытаюсь скачать файл через Telegram…")
    await doc.download(destination_file=target)
    logger.info(f"Saved IPA: {target}")

    # metadata
    meta_file = target.with_suffix(".json")
    if not meta_file.exists():
        meta = extract_ipa_metadata(target)
        meta_to_save = {
            "name": meta["name"],
            "bundleIdentifier": meta["bundleIdentifier"],
            "developerName": meta.get("developerName", "Unknown"),
            "iconURL": meta.get("iconURL", ""),
            "localizedDescription": meta.get("localizedDescription", ""),
            "subtitle": meta.get("subtitle", ""),
            "tintColor": meta.get("tintColor", "3c94fc"),
            "category": meta.get("category", "utilities"),
            "versions": [
                {
                    "downloadURL": f"{os.getenv('SERVER_URL','').rstrip('/')}/repo/packages/{target.name}" if os.getenv("SERVER_URL") else f"/repo/packages/{target.name}",
                    "size": get_file_size(target),
                    "version": meta.get("version", "1.0"),
                    "buildVersion": "1",
                    "date": "",
                    "localizedDescription": meta.get("localizedDescription", ""),
                    "minOSVersion": meta.get("min_ios", "16.0")
                }
            ]
        }
        meta_file.write_text(json.dumps(meta_to_save, indent=4, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Created metadata JSON: {meta_file}")

    await message.answer(f"Файл {doc.file_name} сохранён ✅")


# -----------------------------
# Команда /repo — генерация index.json
# -----------------------------
async def cmd_repo(message: types.Message):
    index_file = BASE / "index.json"
    server_url = os.getenv("SERVER_URL", "").rstrip("/")

    repo_data = {
        "name": "ProjectBW Repository",
        "identifier": "projectbw.ksign-repo",
        "subtitle": "A source for Ksign app",
        "description": "repo projectbw.ru",
        "iconURL": "https://raw.githubusercontent.com/bwproject/projectbw-wiki/refs/heads/master/docs/.vuepress/public/images/logo.png",
        "website": "https://projectbw.ru/ios",
        "tintColor": "3c94fc",
        "apps": []
    }

    for ipa in PACKAGES.glob("*.ipa"):
        meta_file = ipa.with_suffix(".json")
        if meta_file.exists():
            try:
                app_meta = json.loads(meta_file.read_text(encoding="utf-8"))
                repo_data["apps"].append(app_meta)
            except Exception as e:
                logger.warning(f"Bad meta {meta_file}: {e}")
                continue

    index_file.write_text(json.dumps(repo_data, indent=4, ensure_ascii=False), encoding="utf-8")
    logger.info(f"index.json generated ({len(repo_data['apps'])} apps)")
    await message.answer(f"index.json обновлён ({len(repo_data['apps'])} приложений)\n{server_url}/repo/index.json")


# -----------------------------
# Команды /start и /upload
# -----------------------------
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 bw_ipa_repo bot\n\n"
        "• Отправь мне файл .ipa — я сохраню его в репозиторий.\n"
        "• Командой /repo собери новый index.json\n"
        "• /upload — открыть WebApp для загрузки больших файлов"
    )

async def cmd_upload(message: types.Message):
    server = os.getenv("SERVER_URL", "").rstrip("/")
    upload_url = f"{server}/webapp"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Открыть WebApp", web_app=WebAppInfo(url=upload_url))]
        ]
    )
    await message.answer("Открыть WebApp для загрузки IPA:", reply_markup=kb)


# -----------------------------
# Регистрация хэндлеров
# -----------------------------
def register_handlers(dp: Dispatcher):
    dp.message.register(handle_document, lambda m: m.document is not None and m.document.file_name.lower().endswith(".ipa"))
    dp.message.register(cmd_repo, Command(commands=["repo"]))
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_upload, Command(commands=["upload"]))