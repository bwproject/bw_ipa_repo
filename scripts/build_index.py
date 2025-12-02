import requests
import json
import os

# GitHub repo
OWNER = "bwproject"
REPO = "bw_ipa_repo"

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"

# Output file
OUTPUT_FILE = "index.json"

print("Fetching releases from GitHub API...")

response = requests.get(API_URL)
releases = response.json()

packages = []

for release in releases:
    tag = release["tag_name"]
    assets = release["assets"]

    for asset in assets:
        filename = asset["name"]

        if filename.endswith(".ipk"):

            # Извлекаем имя и версию из файла mypkg_1.2.3.ipk
            base = filename.rsplit(".", 1)[0]

            if "_" in base:
                name, version = base.split("_", 1)
            else:
                name = base
                version = tag

            url = asset["browser_download_url"]

            packages.append({
                "name": name,
                "version": version,
                "description": f"Package {name}",
                "url": url
            })

# Формируем index.json
index = {"packages": packages}

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(index, f, indent=4, ensure_ascii=False)

print(f"Created {OUTPUT_FILE}. Packages found: {len(packages)}")