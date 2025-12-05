import json
from pathlib import Path

USERS_FILE = Path("users.json")


def check_access(user_id: int) -> bool:
    """
    Проверка доступа пользователя.
    """
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({"users": []}, indent=4, ensure_ascii=False), encoding="utf-8")
        return False

    data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    return user_id in data.get("users", [])
