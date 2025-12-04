# bot/handlers.py

import json
import logging
import os
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile
from plistlib import load as plist_load
from PIL import Image

import aiohttp
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from bot.utils import get_file_size

logger = logging.getLogger("bot.handlers")

BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Скачивание через Telegram API
# -----------------------------
async def _download_via_telegram_url(bot, file_id: str, dest: Path):
    file_info = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
    logger.info(f"Downloading from Telegram URL: {file_url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fd:
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    fd.write(chunk)


# -----------------------------
# Извлечение Info.plist и данных из IPA
# -----------------------------
def extract_ipa_metadata(ipa_path: Path) -> dict:
    metadata = {}
    try:
        with ZipFile(ipa_path, "r") as zipf:
            # Находим .app папку
            app_paths = [f for f in zipf.namelist() if f.endswith(".app/")]
            if not app_paths:
                return metadata
            app_path = app_paths[0]

            # Находим Info.plist
            plist_files = [f for f in zipf.namelist() if f.startswith(app_path) and f.endswith("Info.plist")]
            if not plist_files:
                return metadata
            plist_file = plist_files[0]

            with zipf.open(plist_file) as f:
                plist_data = plist_load(f)
                metadata["name"] = plist_data.get("CFBundleDisplayName") or plist_data.get("CFBundleName") or ipa_path.stem
                metadata["bundle_id"] = plist_data.get("CFBundleIdentifier") or ipa_path.stem
                metadata["version"] = plist_data.get("CFBundleShortVersionString") or "1.0"
                metadata["developerName"] = plist_data.get("CFBundleName") or "Unknown"
                metadata["localizedDescription"] = plist_data.get("CFBundleGetInfoString") or ""
                metadata["subtitle"] = metadata["name"]
    except Exception as e:
        logger.warning(f"Failed to extract metadata from {ipa_path}: {e}")
    return metadata


# -----------------------------
# Извлечение иконки из IPA
# -----------------------------
def extract_icon(ipa_path: Path) -> str:
    try:
        with ZipFile(ipa_path, "r") as zipf:
            app_paths = [f for f in zipf.namelist() if f.endswith(".app/")]
            if not app_paths:
                return ""
            app_path = app_paths[0]

            pngs = [f for f in zipf.namelist() if f.startswith(app_path) and f.endswith(".png")]
            if not pngs:
                return ""

            icon_file = pngs[0]
            icon_name = f"{ipa_path.stem}.png"
            out_path = IMAGES / icon_name

            with zipf.open(icon_file) as src, open(out_path, "wb") as dst:
                dst.write(src.read())

            return f"/repo/images/{icon_name}"
    except Exception as e:
        logger.warning(f"Failed to extract icon from {ipa_path}: {e}")
        return ""


# -----------------------------
# Обработка документа (.ipa)
# -----------------------------
async def handle_document(message: types.Message, bot):
    doc = message.document
    if not doc or not doc.file_name.lower().endswith(".ipa"):
        await message.answer("Пожалуйста, отправляйте только файлы .ipa")
        return

    target = PACKAGES / doc.file_name
    await message.answer("🔄 Пытаюсь скачать файл через Telegram…")

    try:
        await _download_via_telegram_url(bot, doc.file_id, target)
        logger.info(f"Saved IPA: {target}")

        meta = extract_ipa_metadata(target)
        icon_url = extract_icon(target) or ""

        app_json_file = PACKAGES / f"{meta['bundle_id']}.json"
        if app_json_file.exists():
            with open(app_json_file, "r", encoding="utf-8") as f:
                app_data = json.load(f)
        else:
            app_data = {
                "name": meta["name"],
                "bundleIdentifier": meta["bundle_id"],
                "developerName": meta.get("developerName", "Unknown"),
                "iconURL": icon_url,
                "localizedDescription": meta.get("localizedDescription", ""),
                "subtitle": meta.get("subtitle", meta["name"]),
                "tintColor": "3c94fc",
                "category": "utilities",
                "versions": []
            }

        size = get_file_size(target)
        version_info = {
            "downloadURL": f"{os.getenv('SERVER_URL','')}/repo/packages/{target.name}",
            "size": size,
            "version": meta["version"],
            "buildVersion": "1",
            "date": datetime.now().isoformat(),
            "localizedDescription": meta.get("localizedDescription", ""),
            "minOSVersion": "16.0"
        }
        app_data["versions"].append(version_info)

        if icon_url:
            app_data["iconURL"] = icon_url

        with open(app_json_file, "w", encoding="utf-8") as f:
            json.dump(app_data, f, indent=4, ensure_ascii=False)

        await message.answer(f"Файл {doc.file_name} сохранён ✅ и обновлён JSON приложения {meta['bundle_id']}")

    except TelegramBadRequest as e:
        if "file is too big" in str(e).lower():
            server = os.getenv("SERVER_URL", "").rstrip("/")
            upload_url = f"{server}/webapp"
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="📤 Загрузить IPA через WebApp", web_app=WebAppInfo(url=upload_url))]]
            )
            await message.answer(
                "⚠️ Файл слишком большой для загрузки через Telegram.\nНажмите кнопку ниже:",
                reply_markup=kb
            )
        else:
            logger.exception("TelegramBadRequest during download")
            await message.answer("Ошибка Telegram API ❌")
    except Exception as e:
        logger.exception("Failed to download file")
        await message.answer("Ошибка при скачивании файла ❌")


# -----------------------------
# Команда /repo — генерация index.json
# -----------------------------
async def cmd_repo(message: types.Message):
    server_url = os.getenv("SERVER_URL", "").rstrip("/")
    apps = []

    for json_file in PACKAGES.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            app_data = json.load(f)
            for v in app_data.get("versions", []):
                v["downloadURL"] = f"{server_url}/repo/packages/{Path(v['downloadURL']).name}"
            apps.append(app_data)

    repo_index = {
        "name": "ProjectBW Repository",
        "identifier": "projectbw.ksign-repo",
        "subtitle": "A source for Ksign app",
        "description": "repo projectbw.ru",
        "iconURL": "https://raw.githubusercontent.com/bwproject/projectbw-wiki/refs/heads/master/docs/.vuepress/public/images/logo.png",
        "website": "https://projectbw.ru/ios",
        "tintColor": "3c94fc",
        "apps": apps
    }

    index_file = BASE / "index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(repo_index, f, indent=4, ensure_ascii=False)

    await message.answer(f"index.json обновлён ({len(apps)} apps)\n{server_url}/repo/index.json")


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
        inline_keyboard=[[InlineKeyboardButton(text="📤 Открыть WebApp", web_app=WebAppInfo(url=upload_url))]]
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