# bot/handlers.py

import json
import logging
from pathlib import Path

from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.exceptions import TelegramBadRequest
from bot.handlers_packages import register_packages_handlers

from bot.utils import extract_ipa_metadata, get_file_size

logger = logging.getLogger("bot.handlers")

# Папки
BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)


# ==============================
#  Скачивание через Telegram API
# ==============================
async def _download_via_telegram_url(bot, file_id: str, dest: Path):
    file_info = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

    logger.info(f"Downloading from Telegram URL: {file_url}")

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fd:
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    fd.write(chunk)


# ==============================
#  Обработка документа (.ipa)
# ==============================
async def fix_icon_url(meta: dict, ipa_name: str, server_url: str):
    """
    Приводит iconURL к формату:
    https://server/repo/images/icon.png
    """

    icon_url = meta.get("iconURL", "").strip()

    # Если указали полный URL — не трогаем
    if icon_url.startswith("http://") or icon_url.startswith("https://"):
        return icon_url

    # Если иконка внутри .ipa не извлеклась → пробуем repo/images/<ipa>.png
    guessed_png = IMAGES / (Path(ipa_name).stem + ".png")
    if icon_url == "" and guessed_png.exists():
        return f"{server_url}/repo/images/{guessed_png.name}"

    # Если iconURL начинается с /repo/images/...
    if icon_url.startswith("/"):
        return f"{server_url}{icon_url}"

    # Если пусто и PNG нет
    return ""


async def handle_document(message: types.Message, bot):
    doc = message.document
    if not doc or not doc.file_name.lower().endswith(".ipa"):
        await message.answer("Пожалуйста, отправляйте только файлы .ipa")
        return

    target = PACKAGES / doc.file_name
    await message.answer("🔄 Пытаюсь скачать файл через Telegram…")

    import os
    server_url = os.getenv("SERVER_URL", "").rstrip("/")

    try:
        # --- Скачиваем через Telegram API ---
        await _download_via_telegram_url(bot, doc.file_id, target)
        logger.info(f"Saved IPA: {target}")

        # --- Генерация .json для каждого IPA ---
        meta_file = target.with_suffix(".json")

        if not meta_file.exists():
            meta = extract_ipa_metadata(target)

            # Правильный iconURL
            fixed_icon = await fix_icon_url(meta, target.name, server_url)

            meta_to_save = {
                "name": meta.get("name") or target.stem,
                "bundleIdentifier": meta.get("bundleIdentifier") or f"com.projectbw.{target.stem.lower()}",
                "developerName": meta.get("developerName", "Unknown"),
                "iconURL": fixed_icon,
                "localizedDescription": meta.get("localizedDescription") or "",
                "subtitle": meta.get("subtitle") or "",
                "tintColor": meta.get("tintColor") or "3c94fc",
                "category": meta.get("category") or "utilities",
                "versions": [
                    {
                        "downloadURL": f"{server_url}/repo/packages/{target.name}",
                        "size": get_file_size(target),
                        "version": meta.get("version") or "1.0",
                        "buildVersion": "1",
                        "date": "",
                        "localizedDescription": meta.get("localizedDescription") or "",
                        "minOSVersion": meta.get("min_ios") or "16.0"
                    }
                ]
            }

            meta_file.write_text(json.dumps(meta_to_save, indent=4, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Wrote meta file: {meta_file}")

        await message.answer(f"Файл {doc.file_name} сохранён через Telegram API ✅")

    except TelegramBadRequest as e:
        if "file is too big" in str(e).lower():
            import os
            server = os.getenv("SERVER_URL", "").rstrip("/")
            upload_url = f"{server}/webapp"
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(
                    text="📤 Загрузить IPA через WebApp",
                    web_app=WebAppInfo(url=upload_url)
                )]]
            )
            await message.answer(
                "⚠️ Файл слишком большой для загрузки через Telegram.\n"
                "Нажмите кнопку ниже, чтобы открыть WebApp и загрузить файл:",
                reply_markup=kb
            )
        else:
            logger.exception("TelegramBadRequest during download")
            await message.answer("Ошибка Telegram API ❌")

    except Exception as e:
        logger.exception("Failed to download file")
        await message.answer("Ошибка при скачивании файла ❌")


# ==============================
#  Команда /repo — генерация index.json
# ==============================
async def cmd_repo(message: types.Message):
    import os
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
            except Exception as e:
                logger.warning(f"Bad meta {meta_file}: {e}")
                continue
        else:
            meta = extract_ipa_metadata(ipa)
            app_meta = {
                "name": meta.get("name") or ipa.stem,
                "bundleIdentifier": meta.get("bundleIdentifier") or f"com.projectbw.{ipa.stem.lower()}",
                "developerName": meta.get("developerName") or "Unknown",
                "iconURL": "",
                "localizedDescription": meta.get("localizedDescription") or "",
                "subtitle": meta.get("subtitle") or "",
                "tintColor": meta.get("tintColor") or "3c94fc",
                "category": meta.get("category") or "utilities",
                "versions": [
                    {
                        "downloadURL": f"{server_url}/repo/packages/{ipa.name}",
                        "size": get_file_size(ipa),
                        "version": meta.get("version") or "1.0",
                        "buildVersion": "1",
                        "date": "",
                        "localizedDescription": meta.get("localizedDescription") or "",
                        "minOSVersion": meta.get("min_ios") or "16.0"
                    }
                ]
            }

        # --- Правим iconURL ---
        app_meta["iconURL"] = await fix_icon_url(app_meta, ipa.name, server_url)

        repo_data["apps"].append(app_meta)

    # Сохраняем index.json
    index_file.write_text(json.dumps(repo_data, indent=4, ensure_ascii=False), encoding="utf-8")

    await message.answer(
        f"index.json обновлён ({len(repo_data['apps'])} приложений)\n"
        f"{server_url}/repo/index.json"
    )


# ==============================
#  /start & /upload
# ==============================
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 bw_ipa_repo bot\n\n"
        "• Отправь мне файл .ipa — я сохраню его в репозиторий.\n"
        "• (опционально) добавь рядом .json\n"
        "• /repo — собрать index.json\n"
        "• /upload — открыть WebApp"
    )


async def cmd_upload(message: types.Message):
    import os
    server = os.getenv("SERVER_URL", "").rstrip("/")
    upload_url = f"{server}/webapp"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="📤 Открыть WebApp",
            web_app=WebAppInfo(url=upload_url)
        )]]
    )
    await message.answer("Открыть WebApp:", reply_markup=kb)


# ==============================
#  Регистрация хэндлеров
# ==============================
def register_handlers(dp: Dispatcher):
    dp.message.register(
        handle_document,
        lambda m: m.document is not None and m.document.file_name.lower().endswith(".ipa")
    )
    dp.message.register(cmd_repo, Command(commands=["repo"]))
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_upload, Command(commands=["upload"]))

def register_handlers(dp: Dispatcher):
    ...
    register_packages_handlers(dp)