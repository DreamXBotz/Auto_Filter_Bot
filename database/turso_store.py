"""Turso overflow store for media index metadata.

MongoDB remains the primary store. This module is only used when the configured
MongoDB media database reaches its size threshold.
"""
import asyncio
import logging
import os
import re
from types import SimpleNamespace

import libsql

logger = logging.getLogger(__name__)

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
TURSO_ENABLED = bool(TURSO_DATABASE_URL and TURSO_AUTH_TOKEN)

_COLUMNS = (
    "file_id", "file_unique_id", "file_ref", "file_name", "file_size",
    "file_type", "mime_type", "caption", "cover", "created_at",
)


def _connect():
    if not TURSO_ENABLED:
        raise RuntimeError("Turso is not configured. Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN.")
    conn = libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS media_files (
            file_id TEXT PRIMARY KEY,
            file_unique_id TEXT UNIQUE,
            file_ref TEXT,
            file_name TEXT NOT NULL,
            file_size INTEGER NOT NULL,
            file_type TEXT,
            mime_type TEXT,
            caption TEXT,
            cover TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_files_name ON media_files(file_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_media_files_type ON media_files(file_type)")
    conn.commit()
    return conn


def _run_sync(operation):
    conn = _connect()
    try:
        return operation(conn)
    finally:
        conn.close()


def _row_to_media(row):
    return SimpleNamespace(**dict(zip(_COLUMNS, row)))


async def insert_media(data):
    values = tuple(data.get(key) for key in _COLUMNS[:-1])
    def operation(conn):
        cursor = conn.execute(
            """INSERT OR IGNORE INTO media_files
            (file_id, file_unique_id, file_ref, file_name, file_size,
             file_type, mime_type, caption, cover)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        conn.commit()
        return cursor.rowcount > 0
    return await asyncio.to_thread(_run_sync, operation)


async def find_duplicate(file_id, file_unique_id=None):
    def operation(conn):
        if file_unique_id:
            cursor = conn.execute(
                "SELECT 1 FROM media_files WHERE file_id = ? OR file_unique_id = ? LIMIT 1",
                (file_id, file_unique_id),
            )
        else:
            cursor = conn.execute(
                "SELECT 1 FROM media_files WHERE file_id = ? LIMIT 1", (file_id,)
            )
        return cursor.fetchone() is not None
    return await asyncio.to_thread(_run_sync, operation)


async def search_media(pattern, file_type=None, use_caption=True):
    """Return all Turso matches; regex filtering preserves Mongo search semantics."""
    regex = re.compile(pattern, re.IGNORECASE)
    def operation(conn):
        if file_type:
            cursor = conn.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM media_files WHERE file_type = ? ORDER BY created_at DESC",
                (file_type,),
            )
        else:
            cursor = conn.execute(
                f"SELECT {', '.join(_COLUMNS)} FROM media_files ORDER BY created_at DESC"
            )
        rows = cursor.fetchall()
        matches = []
        for row in rows:
            item = _row_to_media(row)
            if regex.search(item.file_name or "") or (
                use_caption and regex.search(item.caption or "")
            ):
                matches.append(item)
        return matches
    return await asyncio.to_thread(_run_sync, operation)


async def get_media_by_id(file_id):
    def operation(conn):
        cursor = conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM media_files WHERE file_id = ? LIMIT 1",
            (file_id,),
        )
        row = cursor.fetchone()
        return [_row_to_media(row)] if row else []
    return await asyncio.to_thread(_run_sync, operation)


async def recent_media(limit):
    def operation(conn):
        cursor = conn.execute(
            f"SELECT {', '.join(_COLUMNS)} FROM media_files ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        )
        return [_row_to_media(row) for row in cursor.fetchall()]
    return await asyncio.to_thread(_run_sync, operation)


async def delete_by_id(file_id):
    def operation(conn):
        cursor = conn.execute("DELETE FROM media_files WHERE file_id = ?", (file_id,))
        conn.commit()
        return cursor.rowcount
    return await asyncio.to_thread(_run_sync, operation)


async def delete_matching(file_name, file_size, mime_type):
    def operation(conn):
        cursor = conn.execute(
            "DELETE FROM media_files WHERE file_name = ? AND file_size = ? AND mime_type IS ?",
            (file_name, int(file_size), mime_type),
        )
        conn.commit()
        return cursor.rowcount
    return await asyncio.to_thread(_run_sync, operation)


async def delete_all():
    def operation(conn):
        cursor = conn.execute("DELETE FROM media_files")
        conn.commit()
        return cursor.rowcount
    return await asyncio.to_thread(_run_sync, operation)


async def count_media():
    def operation(conn):
        cursor = conn.execute("SELECT COUNT(*) FROM media_files")
        return int(cursor.fetchone()[0])
    return await asyncio.to_thread(_run_sync, operation)
