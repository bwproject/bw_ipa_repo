import zipfile
import plistlib

def extract_ipa_metadata(ipa_path):
    """
    Извлекает name, bundle_id, version и возможные иконки из IPA
    """
    with zipfile.ZipFile(ipa_path, 'r') as zip_ref:
        plist_file = None
        for f in zip_ref.namelist():
            if f.startswith("Payload/") and f.endswith("Info.plist"):
                plist_file = f
                break
        if not plist_file:
            return {}

        with zip_ref.open(plist_file) as f:
            plist = plistlib.load(f)

    # Список иконок
    icons = plist.get("CFBundleIconFiles", [])
    icon_name = icons[0] if icons else None

    return {
        "name": plist.get("CFBundleName"),
        "bundle_id": plist.get("CFBundleIdentifier"),
        "version": plist.get("CFBundleShortVersionString"),
        "icon": icon_name
    }
