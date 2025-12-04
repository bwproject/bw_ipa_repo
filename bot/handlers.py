# handlers.py

import json
import logging
import os
from pathlib import Path

import aiohttp
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from bot.utils import extract_ipa_metadata

logger = logging.getLogger("bot.handlers")

# Папки
BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Функция скачивания через Telegram URL
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
        # --- Пытаемся скачать через Telegram API ---
        await _download_via_telegram_url(bot, doc.file_id, target)
        logger.info(f"Saved IPA: {target}")

        # Meta
        meta = extract_ipa_metadata(target)
        meta.setdefault("name", target.stem)
        meta.setdefault("bundle_id", "/skip")
        meta.setdefault("version", "/skip")
        meta.setdefault("icon", None)

        meta_file = target.with_suffix(".json")

        if not meta_file.exists():
            meta_to_save = {
                "name": meta["name"],
                "bundle_id": meta["bundle_id"] or "/skip",
                "version": meta["version"] or "/skip",
                "icon": meta["icon"] or "/skip"
            }
            meta_file.write_text(
                json.dumps(meta_to_save, indent=4, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.info(f"Wrote meta file: {meta_file}")

        await message.answer(f"Файл {doc.file_name} сохранён через Telegram API ✅")

    except TelegramBadRequest as e:
        # --- Файл слишком большой ---
        if "file is too big" in str(e).lower():
            server = os.getenv("SERVER_URL", "").rstrip("/")
            upload_url = f"{server}/upload"

            logger.warning("File too big for Telegram API — fallback to /upload")

            await message.answer(
                "⚠️ Файл слишком большой для загрузки через Telegram.\n\n"
                f"➡️ Загрузите его вручную сюда:\n{upload_url}"
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
    index_file = BASE / "index.json"
    server_url = os.getenv("SERVER_URL", "").rstrip("/")
    entries = []

    for ipa in PACKAGES.glob("*.ipa"):
        meta = {}
        meta_file = ipa.with_suffix(".json")

        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Bad meta {meta_file}: {e}")
                meta = {}

        meta.setdefault("name", ipa.stem)
        meta.setdefault("bundle_id", "/skip")
        meta.setdefault("version", "/skip")
        meta.setdefault("icon", "/skip")

        meta["url"] = (
            f"{server_url}/repo/packages/{ipa.name}"
            if server_url else f"/repo/packages/{ipa.name}"
        )

        entries.append(meta)

    index_file.write_text(
        json.dumps(entries, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )

    logger.info(f"index.json generated ({len(entries)} entries)")

    await message.answer(
        f"index.json обновлён ({len(entries)} apps)\n"
        f"{os.getenv('SERVER_URL', '')}/repo/index.json"
    )


# -----------------------------
# Команда /start
# -----------------------------
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 bw_ipa_repo bot\n\n"
        "• Отправь мне файл .ipa — я сохраню его в репозиторий.\n"
        "• (опционально) добавь рядом файл .json с метаданными.\n"
        "• Командой /repo собери новый index.json"
    )


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