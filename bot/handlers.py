from aiogram import types, Dispatcher
from pathlib import Path
import json
import logging

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

# =============================
# Получение IPA
# =============================
async def handle_document(message: types.Message):
    if not message.document or not message.document.file_name.endswith(".ipa"):
        await message.answer("Пожалуйста, отправляйте только файлы .ipa")
        return

    file_path = PACKAGES / message.document.file_name
    await message.document.download(destination=file_path)
    logging.info(f"Сохранён файл IPA: {file_path}")
    await message.answer(f"Файл {message.document.file_name} сохранён ✅")

# =============================
# Команда /repo — обновление index.json
# =============================
async def cmd_repo(message: types.Message):
    index_file = BASE_PATH / "index.json"
    index_list = []

    for ipa_file in PACKAGES.iterdir():
        if ipa_file.suffix != ".ipa":
            continue

        # Можно хранить metadata в json рядом с ipa
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

        # Добавляем ссылку на сервер
        meta["url"] = f"{os.getenv('SERVER_URL', '')}/repo/packages/{ipa_file.name}"
        index_list.append(meta)

    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index_list, f, indent=4, ensure_ascii=False)

    logging.info(f"Обновлён index.json с {len(index_list)} файлами")
    await message.answer(f"Репозиторий обновлён ✅\nФайлы: {len(index_list)}")

# =============================
# Регистрация хэндлеров
# =============================
def register_handlers(dp: Dispatcher):
    dp.message.register(handle_document, content_types=[types.ContentType.DOCUMENT])
    dp.message.register(cmd_repo, commands=["repo"])
    dp.message.register(lambda m: m.answer(
        "Привет! Я бот репозитория IPA.\n"
        "Отправляй файлы .ipa, а командой /repo обновляй репозиторий."), commands=["start"])