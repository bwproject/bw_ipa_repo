# bot/handlers.py

# handlers.py

import json
import logging
import os
from pathlib import Path
import zipfile
from PIL import Image
from io import BytesIO

import aiohttp
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from bot.utils import extract_ipa_metadata

logger = logging.getLogger("bot.handlers")

# Папки
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
# Извлечение иконки из IPA
# -----------------------------
def extract_icon(ipa_path: Path) -> str | None:
    """Извлекает первую PNG иконку из IPA и сохраняет её в /repo/images"""
    try:
        with zipfile.ZipFile(ipa_path, 'r') as z:
            # ищем все .png файлы в Payload/*.app/
            png_files = [f for f in z.namelist() if f.endswith(".png") and "AppIcon" in f]
            if not png_files:
                png_files = [f for f in z.namelist() if f.endswith(".png")]
            if not png_files:
                return None

            icon_file = png_files[0]
            icon_data = z.read(icon_file)

            # сохраняем иконку
            ext = Path(icon_file).suffix
            icon_name = f"{ipa_path.stem}{ext}"
            icon_path = IMAGES / icon_name

            with open(icon_path, "wb") as f:
                f.write(icon_data)

            return icon_name
    except Exception as e:
        logger.warning(f"Failed to extract icon from {ipa_path}: {e}")
        return None


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

        # metadata
        meta = extract_ipa_metadata(target)

        # извлекаем иконку
        icon_name = extract_icon(target)
        if icon_name:
            meta["icon"] = f"/repo/images/{icon_name}"

        meta_file = target.with_suffix(".json")
        if not meta_file.exists():
            # сохраняем только доступные поля
            meta_to_save = {}
            for key in ["name", "bundle_id", "version", "min_ios", "desc", "icon"]:
                value = meta.get(key)
                if value:
                    meta_to_save[key] = value

            meta_file.write_text(
                json.dumps(meta_to_save, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info(f"Wrote meta file: {meta_file}")

        await message.answer(f"Файл {doc.file_name} сохранён через Telegram API ✅")

    except TelegramBadRequest as e:
        if "file is too big" in str(e).lower():
            server = os.getenv("SERVER_URL", "").rstrip("/")
            upload_url = f"{server}/webapp"
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📤 Загрузить IPA через WebApp",
                            web_app=WebAppInfo(url=upload_url)
                        )
                    ]
                ]
            )
            await message.answer(
                "⚠️ Файл слишком большой для Telegram.\n"
                "Нажмите кнопку ниже, чтобы открыть WebApp и загрузить файл:",
                reply_markup=kb
            )
        else:
            logger.exception("TelegramBadRequest during download")
            await message.answer("Ошибка Telegram API ❌")

    except Exception as e:
        logger.exception("Failed to download file")
        await message.answer("Ошибка при скачивании файла ❌")


# -----------------------------
# Команда /repo — генерация Ksign/AltStore JSON
# -----------------------------
async def cmd_repo(message: types.Message):
    index_file = BASE / "index.json"
    server_url = os.getenv("SERVER_URL", "").rstrip("/")
    entries = []

    for ipa in PACKAGES.glob("*.ipa"):
        meta_file = ipa.with_suffix(".json")
        meta = {}

        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Bad meta {meta_file}: {e}")
                meta = {}

        # если каких-то полей нет — извлекаем из IPA
        missing_keys = [k for k in ["name", "bundle_id", "version", "min_ios", "desc", "icon"] if k not in meta]
        if missing_keys:
            ipa_meta = extract_ipa_metadata(ipa)
            for key in missing_keys:
                if ipa_meta.get(key):
                    meta[key] = ipa_meta[key]

            # извлекаем иконку если нет
            if "icon" not in meta or not meta["icon"]:
                icon_name = extract_icon(ipa)
                if icon_name:
                    meta["icon"] = f"/repo/images/{icon_name}"

            # обновляем JSON
            meta_file.write_text(
                json.dumps(meta, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )

        # URL на IPA
        meta["url"] = f"{server_url}/repo/packages/{ipa.name}" if server_url else f"/repo/packages/{ipa.name}"

        entries.append(meta)

    # сохраняем единый index.json
    index_file.write_text(
        json.dumps(entries, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    logger.info(f"index.json generated ({len(entries)} entries)")

    await message.answer(
        f"index.json обновлён ({len(entries)} apps)\n{server_url}/repo/index.json"
    )


# -----------------------------
# Команды /start и /upload
# -----------------------------
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 bw_ipa_repo bot\n\n"
        "• Отправь мне файл .ipa — я сохраню его.\n"
        "• (опционально) добавь рядом файл .json с метаданными.\n"
        "• Командой /repo собери новый index.json\n"
        "• /upload — открыть WebApp для загрузки больших файлов"
    )


async def cmd_upload(message: types.Message):
    server = os.getenv("SERVER_URL", "").rstrip("/")
    upload_url = f"{server}/webapp"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Открыть WebApp",
                    web_app=WebAppInfo(url=upload_url)
                )
            ]
        ]
    )
    await message.answer("Открыть WebApp для загрузки IPA:", reply_markup=kb)


# -----------------------------
# Регистрация хэндлеров
# -----------------------------
def register_handlers(dp: Dispatcher):
    dp.message.register(
        handle_document,
        lambda m: m.document is not None and m.document.file_name.lower().endswith(".ipa")
    )
    dp.message.register(cmd_repo, Command(commands=["repo"]))
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_upload, Command(commands=["upload"]))