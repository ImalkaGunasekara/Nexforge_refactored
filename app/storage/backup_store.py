import json
from pathlib import Path

from app.config import BACKUPS_DIR


def ensure_backup_dir() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR


def backup_json_path(name: str, backup_id: int) -> Path:
    ensure_backup_dir()
    return BACKUPS_DIR / f"{name}_{backup_id}.json"


def backup_jsonl_path(name: str, backup_id: int) -> Path:
    ensure_backup_dir()
    return BACKUPS_DIR / f"{name}_{backup_id}.jsonl"


def write_json(name: str, backup_id: int, data):
    path = backup_json_path(name, backup_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def read_json(name: str, backup_id: int):
    path = backup_json_path(name, backup_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_jsonl(name: str, backup_id: int, rows: list[dict]):
    path = backup_jsonl_path(name, backup_id)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def append_jsonl(name: str, backup_id: int, row: dict):
    path = backup_jsonl_path(name, backup_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


def read_jsonl(name: str, backup_id: int) -> list[dict]:
    path = backup_jsonl_path(name, backup_id)
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def json_exists(name: str, backup_id: int) -> bool:
    return backup_json_path(name, backup_id).exists()


def jsonl_exists(name: str, backup_id: int) -> bool:
    return backup_jsonl_path(name, backup_id).exists()


def list_backup_files(backup_id: int) -> list[Path]:
    ensure_backup_dir()
    patterns = [
        f"*_{backup_id}.json",
        f"*_{backup_id}.jsonl",
    ]

    files = []
    for pattern in patterns:
        files.extend(BACKUPS_DIR.glob(pattern))

    return sorted(files)
