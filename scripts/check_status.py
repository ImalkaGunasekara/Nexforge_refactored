#!/usr/bin/env python3
import sqlite3
from pathlib import Path
import sys

# ─── CONFIG ──────────────────────────────────────────────
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"
# ──────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_status.py <backup_id|restore_id> [backup|restore]")
        sys.exit(1)

    job_id = int(sys.argv[1])
    job_type = sys.argv[2] if len(sys.argv) > 2 else "backup"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if job_type == "backup":
        cur.execute("SELECT * FROM backups WHERE id = ?", (job_id,))
    else:
        cur.execute("SELECT * FROM restore_jobs WHERE id = ?", (job_id,))

    row = cur.fetchone()
    conn.close()

    if row:
        print(dict(row))
    else:
        print(f"❌ {job_type} job with ID {job_id} not found.")


if __name__ == "__main__":
    main()