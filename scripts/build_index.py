import json
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
BASE_PATH = Path("repo")
PACKAGES = BASE_PATH / "packages"
IMAGES = BASE_PATH / "images"

def build_index():
    apps = []

    for ipa in PACKAGES.glob("*.ipa"):
        meta_file = ipa.with_suffix(".json")

        if not meta_file.exists():
            continue

        meta = json.loads(meta_file.read_text())

        apps.append({
            "name": meta["name"],
            "bundle_id": meta["bundle_id"],
            "version": meta["version"],
            "icon": f"{BASE_URL}/repo/images/{meta['icon']}",
            "ipa_url": f"{BASE_URL}/repo/packages/{ipa.name}"
        })

    index = {"apps": apps}
    (BASE_PATH / "index.json").write_text(json.dumps(index, indent=4), encoding="utf-8")

if __name__ == "__main__":
    build_index()
