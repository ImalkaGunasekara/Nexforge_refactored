#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_store_by_domain
from app.operations.backup import run_backup

# ─── CONFIG ──────────────────────────────────────────────
STORE = "nexforge-test-same-target-store.myshopify.com"
# ──────────────────────────────────────────────────────────


async def main():
    store = get_store_by_domain(STORE)
    if not store:
        print(f"❌ Store '{STORE}' not found in database. Run OAuth first.")
        return
    if not store.get("access_token"):
        print(f"❌ Store '{STORE}' has no access token. Reinstall the app.")
        return

    print(f"🔄 Starting backup for {STORE}...")
    backup_id = await run_backup(store["id"], STORE, "full")
    print(f"✅ Backup completed with ID: {backup_id}")


if __name__ == "__main__":
    asyncio.run(main())