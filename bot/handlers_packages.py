# bot/handlers_packages.py

import json
import logging
from pathlib import Path

from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

logger = logging.getLogger("bot.packages")

BASE = Path("repo")
PACKAGES = BASE / "packages"


# ===============================
# FSM для редактирования JSON
# ===============================
class EditStates(StatesGroup):
    editing_name = State()
    editing_bundle = State()
    editing_version = State()


# ===============================
# /packages_update — пересоздание JSON
# ===============================
async def cmd_packages_update(message: types.Message):
    import os
    server_url = os.getenv("SERVER_URL", "").rstrip("/")

    count = 0
    for ipa in PACKAGES.glob("*.ipa"):
        meta_file = ipa.with_suffix(".json")
        if not meta_file.exists():
            # Пропускаем, создаётся при загрузке
            continue
        count += 1

    await message.answer(f"♻ JSON файлов: <b>{count}</b> проверено", parse_mode="html")


# ===============================
# /packages_list — показать JSON
# ===============================
async def cmd_packages_list(message: types.Message):
    files = list(PACKAGES.glob("*.json"))
    if not files:
        return await message.answer("❌ В репозитории нет .json файлов")

    msg = "📦 Доступные JSON:\n\n"
    for f in files:
        msg += f"• <b>{f.stem}</b>\n"

    msg += "\nДля редактирования: <code>/packages_edit имя</code>"
    await message.answer(msg, parse_mode="html")


# ===============================
# /packages_edit NAME — открыть редактирование
# ===============================
async def cmd_packages_edit_name(message: types.Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Используй:\n<code>/packages_edit имя</code>", parse_mode="html")

    name = parts[1].strip()
    target = PACKAGES / f"{name}.json"
    if not target.exists():
        return await message.answer("❌ Файл не найден")

    data = json.loads(target.read_text(encoding="utf-8"))
    await state.update_data(file_path=str(target), json_data=data)
    await state.set_state(EditStates.editing_name)

    await message.answer(
        f"📝 Редактирование: <b>{name}.json</b>\n\nВведите новое значение для <b>name</b>:",
        parse_mode="html"
    )


# ===============================
# Редактирование сообщений
# ===============================
async def process_edit_line(message: types.Message, state: FSMContext):
    data = await state.get_data()
    json_data = data["json_data"]
    file_path = Path(data["file_path"])
    current_state = await state.get_state()
    text = message.text.strip()
    if not text:
        return await message.answer("❌ Значение не может быть пустым")

    if current_state == EditStates.editing_name.state:
        json_data["name"] = text
        await state.set_state(EditStates.editing_bundle)
        prompt = "Введите новый <b>bundleIdentifier</b>:"
    elif current_state == EditStates.editing_bundle.state:
        json_data["bundleIdentifier"] = text
        await state.set_state(EditStates.editing_version)
        prompt = "Введите новую <b>версию</b> (versions[0].version):"
    elif current_state == EditStates.editing_version.state:
        if "versions" in json_data and len(json_data["versions"]) > 0:
            json_data["versions"][0]["version"] = text
        await state.clear()
        prompt = "✔ Редактирование завершено!"
    else:
        return

    file_path.write_text(json.dumps(json_data, indent=4, ensure_ascii=False), encoding="utf-8")
    await state.update_data(json_data=json_data)
    await message.answer(prompt, parse_mode="html")


# ===============================
# Регистрация
# ===============================
def register_packages_handlers(dp: Dispatcher):
    dp.message.register(cmd_packages_update, Command("packages_update"))
    dp.message.register(cmd_packages_list, Command("packages_list"))
    dp.message.register(cmd_packages_edit_name, Command("packages_edit"))

    dp.message.register(process_edit_line, EditStates.editing_name)
    dp.message.register(process_edit_line, EditStates.editing_bundle)
    dp.message.register(process_edit_line, EditStates.editing_version)