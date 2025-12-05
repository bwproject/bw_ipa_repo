# bot/assest.py

import json
from pathlib import Path

USERS_FILE = Path("users.json")


def ensure_users_file():
    """
    Создаёт users.json, если он отсутствует.
    """
    if not USERS_FILE.exists():
        USERS_FILE.write_text(
            json.dumps({"users": []}, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )


def check_access(user_id: int) -> bool:
    """
    Проверяет, есть ли доступ у пользователя.
    """
    ensure_users_file()

    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return user_id in data.get("users", [])


def add_user(user_id: int):
    """
    Добавление пользователя в users.json
    """
    ensure_users_file()

    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    if user_id not in data.get("users", []):
        data["users"].append(user_id)
        USERS_FILE.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )


def remove_user(user_id: int):
    """
    Удаление пользователя из users.json
    """
    ensure_users_file()

    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    if user_id in data.get("users", []):
        data["users"].remove(user_id)
        USERS_FILE.write_text(
            json.dumps(data, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )