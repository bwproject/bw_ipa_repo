from aiogram import types
from pathlib import Path
import json

BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"

INDEX_FILE = BASE_PATH / "index.json"


async def build_index(update: types.Message):
    """
    Генерирует index.json из всех JSON файлов в repo/packages
    """
    all_packages = []
    for json_file in PACKAGES.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            all_packages.append(data)
        except Exception as e:
            print(f"Ошибка при чтении {json_file}: {e}")

    INDEX_FILE.write_text(json.dumps(all_packages, indent=4, ensure_ascii=False), encoding="utf-8")
    await update.message.reply(f"✅ index.json обновлён!\nСсылка: /repo/index.json")
