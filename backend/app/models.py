"""自选股模型：SQLite 存储，使用标准库 sqlite3，避免额外依赖。"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app.config import DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist (
    code       TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def list_watchlist() -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute("SELECT code, name, created_at FROM watchlist ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_watch(code: str, name: str) -> dict:
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO watchlist (code, name, created_at) VALUES (?, ?, ?)",
            (code, name, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
        return {"code": code, "name": name}
    finally:
        conn.close()


def remove_watch(code: str) -> bool:
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def is_watched(code: str) -> bool:
    conn = _conn()
    try:
        row = conn.execute("SELECT 1 FROM watchlist WHERE code = ?", (code,)).fetchone()
        return row is not None
    finally:
        conn.close()