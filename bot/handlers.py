from aiogram import types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from bot.states import MetaStates
import json
from pathlib import Path

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"


def skip_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="⏭ Пропустить", callback_data="skip")
    return kb.as_markup()


# -----------------------------
# Начало добавления metadata
# -----------------------------
async def start_metadata(update: types.Message, state: FSMContext):
    await update.answer("✏ Введите <b>name</b> приложения:", reply_markup=skip_keyboard())
    await state.set_state(MetaStates.waiting_for_name)


# -----------------------------
# Поле name
# -----------------------------
async def meta_name(update: types.Message, state: FSMContext):
    await state.update_data(name=update.text)
    await update.answer("Введите <b>bundle_id</b>:", reply_markup=skip_keyboard())
    await state.set_state(MetaStates.waiting_for_bundle)


async def skip_name(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(name=None)
    await callback.message.edit_text("Введите <b>bundle_id</b>:")
    await state.set_state(MetaStates.waiting_for_bundle)


# -----------------------------
# bundle_id
# -----------------------------
async def meta_bundle(update: types.Message, state: FSMContext):
    await state.update_data(bundle_id=update.text)
    await update.answer("Введите <b>version</b>:", reply_markup=skip_keyboard())
    await state.set_state(MetaStates.waiting_for_version)


async def skip_bundle(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(bundle_id=None)
    await callback.message.edit_text("Введите <b>version</b>:")
    await state.set_state(MetaStates.waiting_for_version)


# -----------------------------
# version
# -----------------------------
async def meta_version(update: types.Message, state: FSMContext):
    await state.update_data(version=update.text)
    await update.answer("Введите <b>icon (имя файла)</b>:", reply_markup=skip_keyboard())
    await state.set_state(MetaStates.waiting_for_icon)


async def skip_version(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(version=None)
    await callback.message.edit_text("Введите <b>icon</b>:")
    await state.set_state(MetaStates.waiting_for_icon)


# -----------------------------
# icon
# -----------------------------
async def meta_icon(update: types.Message, state: FSMContext):
    await state.update_data(icon=update.text)
    await finish_metadata(update, state)


async def skip_icon(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(icon=None)
    await finish_metadata(callback.message, state)


# -----------------------------
# Завершение wizard'а
# -----------------------------
async def finish_metadata(message: types.Message, state: FSMContext):
    data = await state.get_data()
    ipa_name = data.get("ipa_name")

    meta = {
        "name": data.get("name"),
        "bundle_id": data.get("bundle_id"),
        "version": data.get("version"),
        "icon": data.get("icon"),
    }

    meta_path = PACKAGES / f"{ipa_name}.json"
    meta_path.write_text(json.dumps(meta, indent=4), encoding="utf-8")

    await message.answer(
        "🎉 <b>Метаданные сохранены!</b>\n\n"
        f"<b>name:</b> {meta['name']}\n"
        f"<b>bundle:</b> {meta['bundle_id']}\n"
        f"<b>version:</b> {meta['version']}\n"
        f"<b>icon:</b> {meta['icon']}"
    )

    await state.clear()