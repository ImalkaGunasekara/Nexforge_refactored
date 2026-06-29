import json
from pathlib import Path

from app.config import REPORTS_DIR


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR


def report_json_path(name: str, run_id: int) -> Path:
    ensure_reports_dir()
    return REPORTS_DIR / f"{name}_{run_id}.json"


def report_text_path(name: str, run_id: int) -> Path:
    ensure_reports_dir()
    return REPORTS_DIR / f"{name}_{run_id}.txt"


def write_json_report(name: str, run_id: int, data):
    path = report_json_path(name, run_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def read_json_report(name: str, run_id: int):
    path = report_json_path(name, run_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_text_report(name: str, run_id: int, content: str):
    path = report_text_path(name, run_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def append_text_report(name: str, run_id: int, content: str):
    path = report_text_path(name, run_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(content)
    return path


def report_exists(name: str, run_id: int) -> bool:
    return report_json_path(name, run_id).exists() or report_text_path(name, run_id).exists()


def list_reports(run_id: int) -> list[Path]:
    ensure_reports_dir()
    patterns = [
        f"*_{run_id}.json",
        f"*_{run_id}.txt",
    ]

    files = []
    for pattern in patterns:
        files.extend(REPORTS_DIR.glob(pattern))

    return sorted(files)
