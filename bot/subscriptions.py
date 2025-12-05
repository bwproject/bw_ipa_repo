# bot/subscriptions.py

import os
from pathlib import Path
from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.access import check_access

BASE = Path("repo")
PACKAGES = BASE / "packages"

# ===============================
# Папки сертификатов
# ===============================
CERT_DIR = Path("sert")
CERT_DIRS = {
    "free": CERT_DIR / "free",
    "se": CERT_DIR / "iphonese",
    "pro": CERT_DIR / "iphone13promax",
}
# Создаём папки при старте бота
for p in CERT_DIRS.values():
    p.mkdir(parents=True, exist_ok=True)

BASE_URL = os.getenv("SERVER_URL", "https://example.com")

# ===============================
# /subscribe — список приложений
# ===============================
async def cmd_subscribe(message: types.Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к подпискам.")
        return

    apps = [f.stem for f in PACKAGES.glob("*.ipa")]
    if not apps:
        await message.answer("❌ Нет доступных приложений.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=app, callback_data=f"sub_app:{app}")]
        for app in apps
    ])

    await message.answer("📱 Выберите приложение для подписки:", reply_markup=kb)


# ===============================
# Callback: выбрали приложение
# ===============================
async def callback_app_select(query: CallbackQuery):
    await query.answer()

    app_name = query.data.split(":", 1)[1]

    if not (PACKAGES / f"{app_name}.ipa").exists():
        await query.message.edit_text("❌ Приложение больше не доступно.")
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("FREE", callback_data=f"sub_cert:{app_name}:free"),
            InlineKeyboardButton("IPHONE SE", callback_data=f"sub_cert:{app_name}:se"),
            InlineKeyboardButton("IPHONE 13 PRO", callback_data=f"sub_cert:{app_name}:pro")
        ]
    ])

    await query.message.edit_text(
        f"📲 Вы выбрали <b>{app_name}</b>\nВыберите сертификат:",
        parse_mode="html",
        reply_markup=kb
    )


# ===============================
# Callback: выбрали сертификат
# ===============================
async def callback_cert_select(query: CallbackQuery):
    await query.answer()

    _, app_name, cert_type = query.data.split(":")
    ipa_file = PACKAGES / f"{app_name}.ipa"
    if not ipa_file.exists():
        await query.message.edit_text("❌ Приложение больше не доступно.")
        return

    cert_path = CERT_DIRS.get(cert_type)
    if not cert_path:
        await query.message.edit_text("❌ Некорректный сертификат.")
        return

    # Формируем ссылку на установку, передавая путь сертификата
    install_url = f"{BASE_URL}/install/{app_name}.ipa?cert={cert_path.name}"

    await query.message.edit_text(
        f"✔ Ссылка для установки <b>{app_name}</b> с сертификатом <b>{cert_type.upper()}</b>:\n{install_url}",
        parse_mode="html"
    )


# ===============================
# Регистрация хэндлеров
# ===============================
def register_subscription_handlers(dp: Dispatcher):
    dp.message.register(cmd_subscribe, Command("subscribe"))
    dp.callback_query.register(callback_app_select, lambda c: c.data.startswith("sub_app:"))
    dp.callback_query.register(callback_cert_select, lambda c: c.data.startswith("sub_cert:"))