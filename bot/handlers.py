from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
import json
from pathlib import Path
import subprocess

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"

PACKAGES.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)

async def upload_ipa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()

    if not file.file_path.endswith(".ipa"):
        await update.message.reply_text("Отправь .ipa файл")
        return

    ipa_path = PACKAGES / update.message.document.file_name
    await file.download_to_drive(str(ipa_path))

    await update.message.reply_text(
        "Теперь отправь JSON с параметрами:\n\n"
        "{\n"
        "  \"name\": \"AppName\",\n"
        "  \"bundle_id\": \"com.test.app\",\n"
        "  \"version\": \"1.0\",\n"
        "  \"icon\": \"icon.png\"\n"
        "}"
    )

    ctx.user_data["last_ipa"] = ipa_path.name


async def upload_meta(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        meta = json.loads(update.message.text)
    except:
        return

    ipa_name = ctx.user_data.get("last_ipa")
    if not ipa_name:
        await update.message.reply_text("Сначала загрузи IPA.")
        return

    meta_path = PACKAGES / f"{ipa_name}.json"
    meta_path.write_text(json.dumps(meta, indent=4), encoding="utf-8")

    await update.message.reply_text("Метаданные сохранены!")


async def build_repo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    subprocess.run(["python3", "scripts/build_index.py"])
    await update.message.reply_text("Репозиторий обновлён!\n\nСсылка:\n/repo/index.json")


def register_handlers(app):
    app.add_handler(MessageHandler(filters.Document.ALL, upload_ipa))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, upload_meta))
    app.add_handler(CommandHandler("repo", build_repo))
