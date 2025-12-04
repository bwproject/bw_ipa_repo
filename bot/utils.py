# bot/utils.py

import zipfile
import plistlib
from pathlib import Path
import shutil
import logging

logger = logging.getLogger("bot.utils")

IMAGES = Path("repo/images")
IMAGES.mkdir(parents=True, exist_ok=True)

def extract_ipa_metadata(ipa_path: Path) -> dict:
    """
    Извлекает метаданные из .ipa файла для Ksign.
    """
    meta = {}
    try:
        with zipfile.ZipFile(ipa_path, "r") as zf:
            # Находим Info.plist внутри Payload/*.app/
            info_plist_path = None
            icon_path = None
            for f in zf.namelist():
                if f.endswith("Info.plist") and f.startswith("Payload/"):
                    info_plist_path = f
                if f.endswith(".png") and "AppIcon" in f:
                    icon_path = f

            if info_plist_path:
                with zf.open(info_plist_path) as plist_file:
                    plist_data = plistlib.load(plist_file)
                    meta["name"] = plist_data.get("CFBundleDisplayName") or plist_data.get("CFBundleName") or ipa_path.stem
                    meta["bundleIdentifier"] = plist_data.get("CFBundleIdentifier", "")
                    meta["version"] = plist_data.get("CFBundleShortVersionString", "1.0")
                    meta["min_ios"] = plist_data.get("MinimumOSVersion", "16.0")
                    meta["localizedDescription"] = plist_data.get("CFBundleGetInfoString", "")
                    meta["subtitle"] = ""
                    meta["tintColor"] = "3c94fc"
                    meta["category"] = "utilities"

            # Извлекаем иконку
            if icon_path:
                icon_filename = f"{ipa_path.stem}.png"
                target_icon = IMAGES / icon_filename
                with zf.open(icon_path) as icon_file, open(target_icon, "wb") as f_out:
                    shutil.copyfileobj(icon_file, f_out)
                meta["iconURL"] = f"/repo/images/{icon_filename}"
            else:
                meta["iconURL"] = ""

    except Exception as e:
        logger.exception(f"Failed to extract metadata from {ipa_path}: {e}")
        meta.setdefault("name", ipa_path.stem)
        meta.setdefault("bundleIdentifier", "")
        meta.setdefault("version", "1.0")
        meta.setdefault("iconURL", "")
        meta.setdefault("min_ios", "16.0")
        meta.setdefault("localizedDescription", "")
        meta.setdefault("subtitle", "")
        meta.setdefault("tintColor", "3c94fc")
        meta.setdefault("category", "utilities")

    return meta

def get_file_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0