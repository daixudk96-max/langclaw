"""SQLite connection manager using aiosqlite."""

from __future__ import annotations

import os
from pathlib import Path

import aiosqlite
from loguru import logger

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_DB_PATH = os.environ.get(
    "RENTAGENT_DB_PATH",
    str(Path(__file__).parents[1] / "rentagent.db"),
)

_db: aiosqlite.Connection | None = None


async def init_db(db_path: str | None = None) -> None:
    """Initialize the database: open connection and apply schema."""
    global _db
    path = db_path or _DB_PATH

    _db = await aiosqlite.connect(path)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA foreign_keys=ON")

    schema = _SCHEMA_PATH.read_text()
    await _db.executescript(schema)

    # Migrations: add columns that may not exist in older databases
    migrations = [
        "ALTER TABLE listings ADD COLUMN research_id TEXT REFERENCES area_research(id)",
        # Auto-scan schedule columns (added for scheduled scanning feature)
        "ALTER TABLE campaigns ADD COLUMN \
            auto_scan_hour INTEGER NOT NULL DEFAULT 6",
        "ALTER TABLE campaigns ADD COLUMN \
            auto_scan_timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh'",
        "ALTER TABLE campaigns ADD COLUMN last_auto_scan_date TEXT",
    ]
    for sql in migrations:
        try:
            await _db.execute(sql)
        except Exception:
            pass  # Column already exists

    await _db.commit()
    logger.info("Database initialized at {}", path)


async def get_db() -> aiosqlite.Connection:
    """Return the active database connection."""
    if _db is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _db


async def close_db() -> None:
    """Close the database connection."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None
        logger.info("Database connection closed")
