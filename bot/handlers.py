# bot/handlers.py

import json
import logging
import os
from pathlib import Path

from aiogram import types, Dispatcher
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.exceptions import TelegramBadRequest

from bot.handlers_packages import register_packages_handlers
from bot.subscriptions import register_subscription_handlers
from bot.utils import extract_ipa_metadata, get_file_size
from bot.access import check_access, add_user, ensure_users_file

logger = logging.getLogger("bot.handlers")

# ==============================
# Директории
# ==============================
BASE = Path("repo")
PACKAGES = BASE / "packages"
IMAGES = BASE / "images"
PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

ensure_users_file()

# ==============================
# Telegram File Downloader
# ==============================
async def _download_via_telegram_url(bot, file_id: str, dest: Path):
    file_info = await bot.get_file(file_id)
    file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"

    logger.info(f"Downloading via Telegram URL: {file_url}")

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            resp.raise_for_status()
            with open(dest, "wb") as fd:
                async for chunk in resp.content.iter_chunked(64 * 1024):
                    fd.write(chunk)

# ==============================
# ICON URL FIX
# ==============================
async def fix_icon_url(meta: dict, ipa_name: str, server_url: str):
    icon_url = meta.get("iconURL", "").strip()

    if icon_url.startswith("http://") or icon_url.startswith("https://"):
        return icon_url

    guessed_png = IMAGES / (Path(ipa_name).stem + ".png")
    if icon_url == "" and guessed_png.exists():
        return f"{server_url}/repo/images/{guessed_png.name}"

    if icon_url.startswith("/"):
        return f"{server_url}{icon_url}"

    return ""

# ==============================
# Обработка .ipa файлов
# ==============================
async def handle_document(message: types.Message, bot):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    doc = message.document
    if not doc or not doc.file_name.lower().endswith(".ipa"):
        await message.answer("Пожалуйста, отправьте файл .ipa")
        return

    target = PACKAGES / doc.file_name
    await message.answer("📥 Скачиваю файл через Telegram…")

    server_url = os.getenv("SERVER_URL", "").rstrip("/")

    try:
        await _download_via_telegram_url(bot, doc.file_id, target)

        meta_file = target.with_suffix(".json")
        if not meta_file.exists():
            meta = extract_ipa_metadata(target)
            fixed_icon = await fix_icon_url(meta, target.name, server_url)

            meta_to_save = {
                "name": meta.get("name") or target.stem,
                "bundleIdentifier": meta.get("bundleIdentifier") or f"com.projectbw.{target.stem.lower()}",
                "developerName": meta.get("developerName", "Unknown"),
                "iconURL": fixed_icon,
                "localizedDescription": meta.get("localizedDescription") or "Описание недоступно.",
                "subtitle": meta.get("subtitle") or "",
                "tintColor": meta.get("tintColor") or "3c94fc",
                "category": meta.get("category") or "utilities",
                "versions": [
                    {
                        "downloadURL": f"{server_url}/repo/packages/{target.name}",
                        "size": get_file_size(target),
                        "version": meta.get("version") or "1.0",
                        "buildVersion": meta.get("build") or "1",
                        "date": meta.get("date") or "",
                        "localizedDescription": meta.get("localizedDescription") or "",
                        "minOSVersion": meta.get("min_ios") or "16.0"
                    }
                ]
            }

            meta_file.write_text(json.dumps(meta_to_save, indent=4, ensure_ascii=False), encoding="utf-8")

        await message.answer(f"✔ Файл {doc.file_name} сохранён")

    except TelegramBadRequest as e:
        if "file is too big" in str(e).lower():
            upload_url = f"{server_url}/webapp"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📤 Загрузить через WebApp",
                    web_app=WebAppInfo(url=upload_url)
                )]
            ])

            await message.answer("⚠️ Файл слишком большой. Используй WebApp:", reply_markup=kb)
        else:
            logger.exception(e)
            await message.answer("❌ Ошибка Telegram API")

    except Exception as e:
        logger.exception(e)
        await message.answer("❌ Ошибка при скачивании файла")

# ====================================================
# NEW: /fixmeta — пересоздать .json у всех IPA
# ====================================================
async def cmd_fixmeta(message: types.Message):
    if not check_access(message.from_user.id):
        return await message.answer("❌ У вас нет доступа.")

    server_url = os.getenv("SERVER_URL", "").rstrip("/")
    created = 0
    report = ""

    for ipa in PACKAGES.glob("*.ipa"):
        meta_file = ipa.with_suffix(".json")
        if meta_file.exists():
            continue

        meta = extract_ipa_metadata(ipa)

        meta_info = {
            "name": meta.get("name") or ipa.stem,
            "bundleIdentifier": meta.get("bundleIdentifier") or f"com.projectbw.{ipa.stem.lower()}",
            "developerName": meta.get("developerName") or "Unknown",
            "iconURL": "",
            "localizedDescription": meta.get("localizedDescription") or "Описание недоступно.",
            "subtitle": "",
            "tintColor": "3c94fc",
            "category": "utilities",
            "versions": [
                {
                    "downloadURL": f"{server_url}/repo/packages/{ipa.name}",
                    "size": get_file_size(ipa),
                    "version": meta.get("version") or "1.0",
                    "buildVersion": meta.get("build") or "1",
                    "date": meta.get("date") or "",
                    "localizedDescription": meta.get("localizedDescription") or "",
                    "minOSVersion": meta.get("min_ios") or "16.0"
                }
            ]
        }

        meta_file.write_text(json.dumps(meta_info, indent=4, ensure_ascii=False), encoding="utf-8")
        created += 1
        report += f"✔ Создан meta: {ipa.stem}.json\n"

    if created == 0:
        await message.answer("✔ Все .json уже существуют.")
    else:
        await message.answer(report + f"\nВсего создано: {created}")

# ==============================
# /repo — генерация index.json
# ==============================
async def cmd_repo(message: types.Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    server_url = os.getenv("SERVER_URL", "").rstrip("/")
    index_file = BASE / "index.json"

    repo_data = {
        "name": "ProjectBW Repository",
        "identifier": "projectbw.ksign-repo",
        "subtitle": "A source for Ksign app",
        "description": "repo projectbw.ru",
        "iconURL": "https://raw.githubusercontent.com/bwproject/projectbw-wiki/refs/heads/master/docs/.vuepress/public/images/logo.png",
        "website": "https://projectbw.ru/ios",
        "tintColor": "3c94fc",
        "apps": []
    }

    updated_count = 0
    updated_names = []

    for ipa in PACKAGES.glob("*.ipa"):
        updated_count += 1
        updated_names.append(ipa.stem)

        meta_file = ipa.with_suffix(".json")
        if meta_file.exists():
            try:
                app_meta = json.loads(meta_file.read_text(encoding="utf-8"))
            except:
                app_meta = {}
        else:
            meta = extract_ipa_metadata(ipa)
            app_meta = {}

        # гарантируем поля
        app_meta.setdefault("name", ipa.stem)
        app_meta.setdefault("bundleIdentifier", f"com.projectbw.{ipa.stem.lower()}")
        app_meta.setdefault("developerName", "Unknown")
        app_meta.setdefault("subtitle", "")
        app_meta.setdefault("tintColor", "3c94fc")
        app_meta.setdefault("category", "utilities")
        app_meta.setdefault("localizedDescription", "Описание недоступно.")

        # иконка
        app_meta["iconURL"] = await fix_icon_url(app_meta, ipa.name, server_url)

        # версии
        if "versions" not in app_meta or not app_meta["versions"]:
            meta = extract_ipa_metadata(ipa)
            app_meta["versions"] = [
                {
                    "downloadURL": f"{server_url}/repo/packages/{ipa.name}",
                    "size": get_file_size(ipa),
                    "version": meta.get("version") or "1.0",
                    "buildVersion": meta.get("build") or "1",
                    "date": meta.get("date") or "",
                    "localizedDescription": app_meta.get("localizedDescription", ""),
                    "minOSVersion": meta.get("min_ios") or "16.0"
                }
            ]
        else:
            app_meta["versions"][0]["downloadURL"] = f"{server_url}/repo/packages/{ipa.name}"
            app_meta["versions"][0]["size"] = get_file_size(ipa)

        repo_data["apps"].append(app_meta)

    # сортировка по имени
    repo_data["apps"].sort(key=lambda x: x["name"].lower())

    index_file.write_text(json.dumps(repo_data, indent=4, ensure_ascii=False), encoding="utf-8")

    apps_list = "\n".join([f"— {n}" for n in sorted(updated_names)])
    repo_url = f"{server_url}/repo/index.json"

    await message.answer(
        f"✔ index.json обновлён\n"
        f" {repo_url} \n\n"
        f"📦 Всего приложений: <b>{updated_count}</b>\n\n"
        f"{apps_list}",
        parse_mode="html"
    )

# ==============================
# /start
# ==============================
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 bw_ipa_repo bot\n\n"
        "• Отправь .ipa — я сохраню его в репозиторий.\n"
        "• /repo — обновить index.json\n"
        "• /fixmeta — пересоздать .json для IPA\n"
        "• /upload — открыть WebApp\n"
        "• /subscribe — подписка на приложения\n"
        "• /add_user USER_ID — дать доступ"
    )

# ==============================
# /upload
# ==============================
async def cmd_upload(message: types.Message):
    if not check_access(message.from_user.id):
        await message.answer("❌ У вас нет доступа к боту.")
        return

    server = os.getenv("SERVER_URL", "").rstrip("/")
    upload_url = f"{server}/webapp"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 WebApp",
            web_app=WebAppInfo(url=upload_url)
        )]
    ])
    await message.answer("Открыть WebApp:", reply_markup=kb)

# ==============================
# /add_user — добавить пользователя
# ==============================
async def cmd_add_user(message: types.Message):
    admin_id = int(os.getenv("ADMIN_ID", "0"))

    if message.from_user.id != admin_id:
        return await message.answer("❌ Только админ может добавлять пользователей.")

    parts = message.text.split()
    if len(parts) != 2:
        return await message.answer("Использование:\n/add_user USER_ID")

    try:
        user_id = int(parts[1])
    except:
        return await message.answer("USER_ID должно быть числом.")

    add_user(user_id)
    await message.answer(f"✔ Пользователь {user_id} добавлен.")

# ==============================
# Регистрация хэндлеров
# ==============================
def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_repo, Command(commands=["repo"]))
    dp.message.register(cmd_fixmeta, Command(commands=["fixmeta"]))
    dp.message.register(cmd_upload, Command(commands=["upload"]))
    dp.message.register(cmd_add_user, Command(commands=["add_user"]))

    dp.message.register(
        handle_document,
        lambda m: m.document is not None and m.document.file_name.lower().endswith(".ipa")
    )

    register_packages_handlers(dp)
    register_subscription_handlers(dp)