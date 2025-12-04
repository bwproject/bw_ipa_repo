# bot/handlers_packages.py

import json
import logging
from pathlib import Path

from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from bot.utils import extract_ipa_metadata, get_file_size

logger = logging.getLogger("bot.packages")

BASE = Path("repo")
PACKAGES = BASE / "packages"


# ======================================================
# FSM для редактирования JSON
# ======================================================
class EditStates(StatesGroup):
    editing = State()


# ======================================================
# Исправленный fix_icon_url
# ======================================================
async def fix_icon_url(meta: dict, ipa_name: str, server_url: str):
    icon_url = meta.get("iconURL", "").strip()

    # Полный URL – оставляем
    if icon_url.startswith("http://") or icon_url.startswith("https://"):
        return icon_url

    # Если пусто – ищем PNG в repo/images
    png_path = Path("repo/images") / (Path(ipa_name).stem + ".png")
    if (not icon_url) and png_path.exists():
        return f"{server_url}/repo/images/{png_path.name}"

    # Если начинается с /repo/…
    if icon_url.startswith("/"):
        return f"{server_url}{icon_url}"

    return ""


# ======================================================
# /packages_update — Перегнать все JSON
# ======================================================
async def cmd_packages_update(message: types.Message):
    import os
    server_url = os.getenv("SERVER_URL", "").rstrip("/")

    count = 0

    for ipa in PACKAGES.glob("*.ipa"):
        meta = extract_ipa_metadata(ipa)
        fixed_icon = await fix_icon_url(meta, ipa.name, server_url)

        meta_file = ipa.with_suffix(".json")

        new_json = {
            "name": meta.get("name") or ipa.stem,
            "bundleIdentifier": meta.get("bundleIdentifier") or f"com.projectbw.{ipa.stem.lower()}",
            "developerName": meta.get("developerName") or "Unknown",
            "iconURL": fixed_icon,
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

        meta_file.write_text(json.dumps(new_json, indent=4, ensure_ascii=False), encoding="utf-8")
        count += 1

    await message.answer(f"♻ Обновлено JSON файлов: <b>{count}</b>", parse_mode="html")


# ======================================================
# /packages_list — вывод списка json
# ======================================================
async def cmd_packages_list(message: types.Message):
    files = list(PACKAGES.glob("*.json"))
    if not files:
        return await message.answer("❌ В репозитории нет .json файлов")

    msg = "📦 Доступные JSON:\n\n"
    for f in files:
        msg += f"• <b>{f.stem}</b>\n"

    msg += "\nДля редактирования: <code>/packages_edit имя</code>"

    await message.answer(msg, parse_mode="html")


# ======================================================
# /packages_edit NAME — открыть файл
# ======================================================
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

    formatted = json.dumps(data, indent=4, ensure_ascii=False)

    await message.answer(
        f"📝 Редактирование: <b>{name}.json</b>\n\n"
        f"<pre>{formatted}</pre>\n\n"
        f"Введи строку в формате:\n"
        f"<code>ключ: значение</code>\n"
        f"Поддерживаются вложенные ключи:\n"
        f"<code>versions.0.version: 2.0</code>",
        parse_mode="html"
    )

    await state.set_state(EditStates.editing)


# ======================================================
# Редактирование строки
# ======================================================
def set_nested_value(data, dotted_key, value):
    keys = dotted_key.split(".")
    d = data
    for k in keys[:-1]:
        if k.isdigit():
            k = int(k)
        d = d[k]
    last = keys[-1]
    if last.isdigit():
        last = int(last)
    d[last] = value
    return data


async def process_edit_line(message: types.Message, state: FSMContext):
    text = message.text

    if ":" not in text:
        return await message.answer("Формат: <code>ключ: значение</code>", parse_mode="html")

    key, value = [t.strip() for t in text.split(":", 1)]

    data = await state.get_data()
    json_data = data["json_data"]
    file_path = Path(data["file_path"])

    try:
        set_nested_value(json_data, key, value)
    except Exception:
        return await message.answer("❌ Ошибка: ключ не найден или неверный путь")

    file_path.write_text(json.dumps(json_data, indent=4, ensure_ascii=False), encoding="utf-8")
    await state.update_data(json_data=json_data)

    await message.answer("✔ Обновлено! Введи следующую строку.")


# ======================================================
# Регистрация
# ======================================================
def register_packages_handlers(dp: Dispatcher):
    dp.message.register(cmd_packages_update, Command("packages_update"))
    dp.message.register(cmd_packages_list, Command("packages_list"))
    dp.message.register(cmd_packages_edit_name, Command("packages_edit"))

    dp.message.register(process_edit_line, EditStates.editing)