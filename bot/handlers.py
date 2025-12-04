# handlers.py

from aiogram import types, Dispatcher
from aiogram.filters import Command
from pathlib import Path
import json
import logging
import os
import aiohttp

from bot.utils import extract_ipa_metadata

logger = logging.getLogger("bot.handlers")

BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

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

async def handle_document(message: types.Message, bot):
    doc = message.document
    if not doc or not doc.file_name.lower().endswith(".ipa"):
        await message.answer("Пожалуйста, отправляйте только файлы .ipa")
        return

    target = PACKAGES / doc.file_name
    await message.answer("Скачиваю файл (может занять время) …")
    try:
        await _download_via_telegram_url(bot, doc.file_id, target)
        logger.info(f"Saved IPA: {target}")

        # extract metadata and save JSON next to IPA if not exists
        meta = extract_ipa_metadata(target)
        # fill defaults
        meta.setdefault("name", target.stem)
        meta.setdefault("bundle_id", "/skip")
        meta.setdefault("version", "/skip")
        meta.setdefault("icon", None)

        meta_file = target.with_suffix(".json")
        # do not overwrite existing manual metadata; only create if absent
        if not meta_file.exists():
            meta_to_save = {
                "name": meta["name"],
                "bundle_id": meta["bundle_id"] or "/skip",
                "version": meta["version"] or "/skip",
                "icon": meta["icon"] or "/skip"
            }
            meta_file.write_text(json.dumps(meta_to_save, indent=4, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Wrote meta file: {meta_file}")
        await message.answer(f"Файл {doc.file_name} сохранён ✅")
    except Exception as e:
        logger.exception("Failed to download file")
        await message.answer("Ошибка при скачивании файла ❌")

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
        url = f"{server_url}/repo/packages/{ipa.name}" if server_url else f"/repo/packages/{ipa.name}"
        meta["url"] = url
        entries.append(meta)

    index_file.write_text(json.dumps(entries, indent=4, ensure_ascii=False), encoding="utf-8")
    logger.info(f"index.json generated ({len(entries)} entries)")
    await message.answer(f"index.json обновлён ({len(entries)} entries)\n{os.getenv('SERVER_URL','')}/repo/index.json")

async def cmd_start(message: types.Message):
    await message.answer(
        "👋 bw_ipa_repo bot\n\n"
        "• Отправь .ipa — я сохраню.\n"
        "• По желанию добавь рядом файл MyApp.ipa.json с метаданными.\n"
        "• Выполни /repo — соберу repo/index.json"
    )

def register_handlers(dp: Dispatcher):
    # document filter: only .ipa
    dp.message.register(handle_document, lambda m: m.document is not None and m.document.file_name.lower().endswith(".ipa"))
    dp.message.register(cmd_repo, Command(commands=["repo"]))
    dp.message.register(cmd_start, Command(commands=["start"]))