# bot/subscriptions.py

import os
from pathlib import Path
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, Text
from bot.access import check_access

# ===============================
# Пути и сертификаты
# ===============================
BASE = Path("repo")
PACKAGES = BASE / "packages"

CERTS = {
    "free": os.getenv("CERT_FREE", "free_cert.mobileprovision"),
    "se": os.getenv("CERT_SE", "se_cert.mobileprovision"),
    "pro": os.getenv("CERT_PRO", "pro_cert.mobileprovision"),
}

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

    kb = InlineKeyboardMarkup(row_width=1)
    for app in apps:
        kb.add(InlineKeyboardButton(text=app, callback_data=f"sub_app:{app}"))

    await message.answer("📱 Выберите приложение для подписки:", reply_markup=kb)


# ===============================
# Callback: выбрали приложение
# ===============================
async def callback_app_select(query: CallbackQuery):
    await query.answer()

    app_name = query.data.split(":", 1)[1]

    ipa_path = PACKAGES / f"{app_name}.ipa"
    if not ipa_path.exists():
        await query.message.edit_text("❌ Приложение больше не доступно.")
        return

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("FREE", callback_data=f"sub_cert:{app_name}:free"),
        InlineKeyboardButton("IPHONE SE", callback_data=f"sub_cert:{app_name}:se"),
        InlineKeyboardButton("IPHONE 13 PRO", callback_data=f"sub_cert:{app_name}:pro"),
    )

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

    cert_file = CERTS.get(cert_type)
    if not cert_file:
        await query.message.edit_text("❌ Некорректный сертификат.")
        return

    install_url = f"{BASE_URL}/install/{app_name}.ipa?cert={cert_file}"

    await query.message.edit_text(
        f"✔ Ссылка для установки <b>{app_name}</b> с сертификатом <b>{cert_type.upper()}</b>:\n{install_url}",
        parse_mode="html"
    )


# ===============================
# Регистрация хэндлеров
# ===============================
def register_subscription_handlers(dp: Dispatcher):
    dp.message.register(cmd_subscribe, Command("subscribe"))
    dp.callback_query.register(callback_app_select, Text(startswith="sub_app:"))
    dp.callback_query.register(callback_cert_select, Text(startswith="sub_cert:"))