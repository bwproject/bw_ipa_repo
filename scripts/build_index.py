import os
import json

GITHUB_RAW = "https://raw.githubusercontent.com/bwproject/bw_ipa_repo/main/packages/"

PACKAGES_DIR = "packages"
OUTPUT_FILE = "index.json"

packages = []

# Перебираем ipk-файлы
for filename in os.listdir(PACKAGES_DIR):
    if filename.endswith(".ipk"):
        base = filename.rsplit(".", 1)[0]

        # Извлекаем версию из имени файла mypkg_1.0.0.ipk → name=mypkg version=1.0.0
        if "_" in base:
            name, version = base.split("_", 1)
        else:
            name = base
            version = "1.0.0"

        packages.append({
            "name": name,
            "version": version,
            "description": f"Package {name}",
            "url": GITHUB_RAW + filename
        })

# Итоговая структура
index = {"packages": packages}

# Запись index.json
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, indent=4, ensure_ascii=False)

print(f"index.json создан. Пакетов: {len(packages)}")
