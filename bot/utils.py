import zipfile
import plistlib
from pathlib import Path
import shutil
from typing import Dict, Any

IMAGES = Path("repo/images")
IMAGES.mkdir(parents=True, exist_ok=True)

def extract_ipa_metadata(ipa_path: Path) -> Dict[str, Any]:
    """Extract name, bundle_id, version and save first icon as <bundle>.png if possible."""
    if not ipa_path.exists():
        return {}

    with zipfile.ZipFile(ipa_path, "r") as z:
        plist_path = None
        app_folder = None
        for p in z.namelist():
            if p.startswith("Payload/") and p.endswith("Info.plist"):
                plist_path = p
                app_folder = "/".join(p.split("/")[:-1]) + "/"
                break
        if not plist_path:
            return {}

        with z.open(plist_path) as f:
            plist = plistlib.load(f)

        name = plist.get("CFBundleDisplayName") or plist.get("CFBundleName")
        bundle = plist.get("CFBundleIdentifier")
        version = plist.get("CFBundleShortVersionString")
        icons = plist.get("CFBundleIconFiles", []) or []

        saved_icon = None
        if icons and bundle and app_folder:
            icon_base = icons[0]
            for ext in (".png", ".jpg", ".jpeg"):
                candidate = app_folder + icon_base + ext
                if candidate in z.namelist():
                    saved_icon = f"{bundle}.png"
                    with z.open(candidate) as src, open(IMAGES / saved_icon, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    break

        return {"name": name, "bundle_id": bundle, "version": version, "icon": saved_icon}