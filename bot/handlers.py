from aiogram import types, Dispatcher
from aiogram.filters import Command
from pathlib import Path
import json
import logging
import os

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Хэндлер для файлов IPA
# -----------------------------
async def handle_document(message: types.Message):
    if message.document and message.document.file_name.endswith(".ipa"):
        file_path = PACKAGES / message.document.file_name
        await message.document.download(destination=file_path)
        logging.info(f"Сохранён файл IPA: {file_path}")
        await message.answer(f"Файл {message.document.file_name} сохранён ✅")
    else:
        await message.answer("Пожалуйста, отправляйте только файлы .ipa")

# -----------------------------
# Команда /repo — генерация index.json
# -----------------------------
async def cmd_repo(message: types.Message):
    index_file = BASE_PATH / "index.json"
    index_list = []

    for ipa_file in PACKAGES.iterdir():
        if ipa_file.suffix != ".ipa":
            continue

        meta_file = ipa_file.with_suffix(".json")
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            meta = {
                "name": ipa_file.stem,
                "bundle_id": "/skip",
                "version": "/skip",
                "icon": "/skip"
            }

        meta["url"] = f"{os.getenv('SERVER_URL', '')}/repo/packages/{ipa_file.name}"
        index_list.append(meta)

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_list, f, indent=4, ensure_ascii=False)

    logging.info(f"Обновлён index.json с {len(index_list)} файлами")
    await message.answer(f"Репозиторий обновлён ✅\nФайлы: {len(index_list)}")

# -----------------------------
# Команда /start
# -----------------------------
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот репозитория IPA.\n"
        "Отправляй файлы .ipa, а командой /repo обновляй репозиторий."
    )

# -----------------------------
# Регистрация хэндлеров
# -----------------------------
def register_handlers(dp: Dispatcher):
    # Для документов используем фильтр через lambda
    dp.message.register(handle_document, lambda m: m.document is not None and m.document.file_name.endswith(".ipa"))

    # Для команд используем фильтры Command
    dp.message.register(cmd_repo, Command(commands=["repo"]))
    dp.message.register(cmd_start, Command(commands=["start"]))