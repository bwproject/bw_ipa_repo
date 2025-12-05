# bot/handlers_packages.py

import json
import logging
from pathlib import Path

from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.access import check_access

logger = logging.getLogger("bot.packages")

BASE = Path("repo")
PACKAGES = BASE / "packages"


class EditStates(StatesGroup):
    editing_name = State()
    editing_bundle = State()
    editing_version = State()


# /packages_update
async def cmd_packages_update(message: types.Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    count = len(list(PACKAGES.glob("*.json")))
    await message.answer(f"♻ Найдено JSON файлов: <b>{count}</b>", parse_mode="html")


# /packages_list
async def cmd_packages_list(message: types.Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    files = list(PACKAGES.glob("*.json"))
    if not files:
        return await message.answer("❌ Нет .json файлов")

    msg = "📦 JSON файлы:\n\n"
    for f in files:
        msg += f"• <b>{f.stem}</b>\n"

    msg += "\nДля редактирования: <code>/packages_edit имя</code>"
    await message.answer(msg, parse_mode="html")


# /packages_edit NAME
async def cmd_packages_edit_name(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        return await message.answer("Пример:\n<code>/packages_edit esign</code>", parse_mode="html")

    name = parts[1].strip()
    target = PACKAGES / f"{name}.json"

    if not target.exists():
        return await message.answer("❌ JSON не найден")

    data = json.loads(target.read_text(encoding="utf-8"))

    await state.update_data(file_path=str(target), json_data=data)
    await state.set_state(EditStates.editing_name)

    await message.answer(
        f"📝 Редактируем <b>{name}.json</b>\nВведите новое значение поля <b>name</b>:",
        parse_mode="html"
    )


# FSM обработчик
async def process_edit_line(message: types.Message, state: FSMContext):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    data = await state.get_data()
    json_data = data["json_data"]
    file_path = Path(data["file_path"])
    current_state = await state.get_state()

    value = message.text.strip()
    if not value:
        return await message.answer("❌ Пустое значение.")

    if current_state == EditStates.editing_name.state:
        json_data["name"] = value
        await state.set_state(EditStates.editing_bundle)
        prompt = "Введите новое значение <b>bundleIdentifier</b>:"

    elif current_state == EditStates.editing_bundle.state:
        json_data["bundleIdentifier"] = value
        await state.set_state(EditStates.editing_version)
        prompt = "Введите новую версию <b>versions[0].version</b>:"

    elif current_state == EditStates.editing_version.state:
        if "versions" not in json_data or len(json_data["versions"]) == 0:
            json_data["versions"] = [{}]

        json_data["versions"][0]["version"] = value
        await state.clear()
        prompt = "✔ Изменения сохранены!"

    else:
        return

    file_path.write_text(json.dumps(json_data, indent=4, ensure_ascii=False), encoding="utf-8")
    await state.update_data(json_data=json_data)

    await message.answer(prompt, parse_mode="html")


def register_packages_handlers(dp: Dispatcher):
    dp.message.register(cmd_packages_update, Command("packages_update"))
    dp.message.register(cmd_packages_list, Command("packages_list"))
    dp.message.register(cmd_packages_edit_name, Command("packages_edit"))

    dp.message.register(process_edit_line, EditStates.editing_name)
    dp.message.register(process_edit_line, EditStates.editing_bundle)
    dp.message.register(process_edit_line, EditStates.editing_version)