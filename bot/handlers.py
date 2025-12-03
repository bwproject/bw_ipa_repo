from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.states import MetaStates
from bot.utils import extract_ipa_metadata
from pathlib import Path
import json

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)


def choice_keyboard(value):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"✅ Принять ({value})", callback_data=f"accept_{value}")
    kb.button(text="⏭ Пропустить", callback_data="skip")
    return kb.as_markup()


async def start_metadata(update: types.Message, state: FSMContext):
    ipa_file = update.message.document
    ipa_path = PACKAGES / ipa_file.file_name
    await ipa_file.get_file().download(ipa_path)

    meta = extract_ipa_metadata(ipa_path)
    await state.update_data(ipa_file=ipa_file.file_name, meta=meta)

    value = meta.get("name") or "не найдено"
    await update.message.answer(f"Введите name приложения или примите предложенное:", reply_markup=choice_keyboard(value))
    await state.set_state(MetaStates.waiting_for_name)


async def meta_name(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    meta = data.get("meta", {})
    if callback.data.startswith("accept_"):
        meta["name"] = callback.data.replace("accept_", "")
    await state.update_data(meta=meta)
    value = meta.get("bundle_id") or "не найдено"
    await callback.message.edit_text(f"Введите bundle_id приложения или примите предложенное:", reply_markup=choice_keyboard(value))
    await state.set_state(MetaStates.waiting_for_bundle)


async def meta_bundle(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    meta = data.get("meta", {})
    if callback.data.startswith("accept_"):
        meta["bundle_id"] = callback.data.replace("accept_", "")
    await state.update_data(meta=meta)
    value = meta.get("version") or "не найдено"
    await callback.message.edit_text(f"Введите version приложения или примите предложенное:", reply_markup=choice_keyboard(value))
    await state.set_state(MetaStates.waiting_for_version)


async def meta_version(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    meta = data.get("meta", {})
    if callback.data.startswith("accept_"):
        meta["version"] = callback.data.replace("accept_", "")
    await state.update_data(meta=meta)
    value = meta.get("icon") or "не найдено"
    await callback.message.edit_text(f"Введите имя иконки приложения или примите предложенное:", reply_markup=choice_keyboard(value))
    await state.set_state(MetaStates.waiting_for_icon)


async def meta_icon(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    meta = data.get("meta", {})
    ipa_file = data.get("ipa_file")
    if callback.data.startswith("accept_"):
        meta["icon"] = callback.data.replace("accept_", "")

    # Сохраняем JSON
    meta_path = PACKAGES / f"{ipa_file}.json"
    meta_path.write_text(json.dumps(meta, indent=4, ensure_ascii=False), encoding="utf-8")

    await callback.message.edit_text(f"🎉 Метаданные сохранены!\n\n{json.dumps(meta, indent=2, ensure_ascii=False)}")
    await state.clear()


def register_handlers(dp):
    dp.message.register(start_metadata, F.document)
    dp.callback_query.register(meta_name, MetaStates.waiting_for_name)
    dp.callback_query.register(meta_bundle, MetaStates.waiting_for_bundle)
    dp.callback_query.register(meta_version, MetaStates.waiting_for_version)
    dp.callback_query.register(meta_icon, MetaStates.waiting_for_icon)