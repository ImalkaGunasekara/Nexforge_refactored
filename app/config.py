import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04")
SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID", "")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")

APP_URL = os.getenv("APP_URL", "").rstrip("/")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

BACKUPS_DIR = DATA_DIR / "backups"
REPORTS_DIR = DATA_DIR / "reports"
INVENTORY_DIR = DATA_DIR / "inventory"
EXPORTS_DIR = DATA_DIR / "exports"

for path in [DATA_DIR, BACKUPS_DIR, REPORTS_DIR, INVENTORY_DIR, EXPORTS_DIR]:
    path.mkdir(parents=True, exist_ok=True)
