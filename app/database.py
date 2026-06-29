import sqlite3
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR

DB_PATH = DATA_DIR / "app.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT UNIQUE NOT NULL,
            access_token TEXT,
            refresh_token TEXT,
            scopes TEXT,
            webhook_secret TEXT,
            default_location_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS token_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT NOT NULL,
            event_type TEXT NOT NULL,
            old_access TEXT,
            new_access TEXT,
            old_refresh TEXT,
            new_refresh TEXT,
            old_scopes TEXT,
            new_scopes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            backup_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            s3_path TEXT,
            error_message TEXT,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS restore_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            backup_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (backup_id) REFERENCES backups(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            store_id INTEGER NOT NULL,
            backup_id INTEGER,
            mode TEXT,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (store_id) REFERENCES stores(id),
            FOREIGN KEY (backup_id) REFERENCES backups(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_store_id INTEGER NOT NULL,
            target_domain TEXT NOT NULL,
            target_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_store_id) REFERENCES stores(id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS processed_webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn.commit()
    conn.close()


def _row_to_dict(row):
    return dict(row) if row else None


def get_store_by_domain(domain: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM stores WHERE domain = ?", (domain,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def get_store_by_id(store_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM stores WHERE id = ?", (store_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def get_stores():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM stores ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_store(
    domain: str,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    scopes: Optional[str] = None,
    webhook_secret: Optional[str] = None,
    default_location_id: Optional[str] = None,
):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO stores (domain, access_token, refresh_token, scopes, webhook_secret, default_location_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (domain, access_token, refresh_token, scopes, webhook_secret, default_location_id),
    )
    conn.commit()
    store_id = cur.lastrowid
    conn.close()
    return store_id


def update_store_tokens(domain: str, access_token: str, refresh_token: Optional[str], scopes: Optional[str] = None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE stores
        SET access_token = ?, refresh_token = ?, scopes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE domain = ?
        """,
        (access_token, refresh_token, scopes, domain),
    )
    conn.commit()
    conn.close()


def clear_store_tokens(domain: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE stores
        SET access_token = NULL, refresh_token = NULL, updated_at = CURRENT_TIMESTAMP
        WHERE domain = ?
        """,
        (domain,),
    )
    conn.commit()
    conn.close()


def update_store_webhook_secret(domain: str, webhook_secret: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE stores
        SET webhook_secret = ?, updated_at = CURRENT_TIMESTAMP
        WHERE domain = ?
        """,
        (webhook_secret, domain),
    )
    conn.commit()
    conn.close()


def update_store_default_location(domain: str, default_location_id: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE stores
        SET default_location_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE domain = ?
        """,
        (default_location_id, domain),
    )
    conn.commit()
    conn.close()


def log_token_event(
    domain: str,
    event_type: str,
    old_access: Optional[str] = None,
    new_access: Optional[str] = None,
    old_refresh: Optional[str] = None,
    new_refresh: Optional[str] = None,
    old_scopes: Optional[str] = None,
    new_scopes: Optional[str] = None,
):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO token_events (
            domain, event_type, old_access, new_access,
            old_refresh, new_refresh, old_scopes, new_scopes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (domain, event_type, old_access, new_access, old_refresh, new_refresh, old_scopes, new_scopes),
    )
    conn.commit()
    conn.close()


def create_backup_record(store_id: int, backup_type: str, s3_path: Optional[str] = None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO backups (store_id, backup_type, s3_path)
        VALUES (?, ?, ?)
        """,
        (store_id, backup_type, s3_path),
    )
    conn.commit()
    backup_id = cur.lastrowid
    conn.close()
    return backup_id


def update_backup_status(backup_id: int, status: str, error_message: Optional[str] = None, completed_at: Optional[str] = None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE backups
        SET status = ?, error_message = ?, completed_at = COALESCE(?, completed_at)
        WHERE id = ?
        """,
        (status, error_message, completed_at, backup_id),
    )
    conn.commit()
    conn.close()


def get_backup(backup_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM backups WHERE id = ?", (backup_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def get_backups_for_store(store_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM backups WHERE store_id = ? ORDER BY id DESC",
        (store_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_restore_job(store_id: int, backup_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO restore_jobs (store_id, backup_id)
        VALUES (?, ?)
        """,
        (store_id, backup_id),
    )
    conn.commit()
    restore_id = cur.lastrowid
    conn.close()
    return restore_id


def update_restore_status(restore_id: int, status: str, error_message: Optional[str] = None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE restore_jobs
        SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, error_message, restore_id),
    )
    conn.commit()
    conn.close()


def get_restore_job(restore_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM restore_jobs WHERE id = ?", (restore_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def create_sync_job(store_id: int, backup_id: Optional[int], mode: Optional[str]):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO sync_jobs (store_id, backup_id, mode)
        VALUES (?, ?, ?)
        """,
        (store_id, backup_id, mode),
    )
    conn.commit()
    sync_id = cur.lastrowid
    conn.close()
    return sync_id


def update_sync_status(sync_id: int, status: str, error_message: Optional[str] = None):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE sync_jobs
        SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, error_message, sync_id),
    )
    conn.commit()
    conn.close()


def get_sync_job(sync_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM sync_jobs WHERE id = ?", (sync_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_dict(row)


def add_clone(source_store_id: int, target_domain: str, target_token: Optional[str]):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO clones (source_store_id, target_domain, target_token)
        VALUES (?, ?, ?)
        """,
        (source_store_id, target_domain, target_token),
    )
    conn.commit()
    clone_id = cur.lastrowid
    conn.close()
    return clone_id


def mark_webhook_processed(event_id: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO processed_webhooks (event_id)
        VALUES (?)
        """,
        (event_id,),
    )
    conn.commit()
    conn.close()


def is_webhook_processed(event_id: str):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM processed_webhooks WHERE event_id = ?",
        (event_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None
