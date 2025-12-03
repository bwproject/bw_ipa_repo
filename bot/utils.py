import zipfile
import plistlib
from pathlib import Path
import shutil

IMAGES = Path("repo/images")
IMAGES.mkdir(parents=True, exist_ok=True)

def extract_ipa_metadata(ipa_path: Path):
    """
    Извлекает name, bundle_id, version и первую иконку из IPA.
    Сохраняет иконку в repo/images/<bundle_id>.png
    """
    with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
        plist_file = None
        app_folder = None
        for f in zip_ref.namelist():
            if f.startswith("Payload/") and f.endswith("Info.plist"):
                plist_file = f
                app_folder = "/".join(f.split("/")[:-1]) + "/"
                break
        if not plist_file:
            return {}

        with zip_ref.open(plist_file) as f:
            plist = plistlib.load(f)

        icons = plist.get("CFBundleIconFiles", [])
        icon_name = icons[0] if icons else None

        bundle_id = plist.get("CFBundleIdentifier", "unknown_bundle")
        saved_icon_name = None
        if icon_name:
            for ext in [".png", ".jpg", ".jpeg"]:
                icon_path_in_ipa = app_folder + icon_name + ext
                if icon_path_in_ipa in zip_ref.namelist():
                    saved_icon_name = f"{bundle_id}.png"
                    with zip_ref.open(icon_path_in_ipa) as icon_file, open(IMAGES / saved_icon_name, "wb") as out_file:
                        shutil.copyfileobj(icon_file, out_file)
                    break

    return {
        "name": plist.get("CFBundleName"),
        "bundle_id": bundle_id,
        "version": plist.get("CFBundleShortVersionString"),
        "icon": saved_icon_name
    }