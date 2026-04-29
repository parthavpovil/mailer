import asyncio
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("APP_DB_PATH", "app.db"))


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS email_suppressions (
            email TEXT PRIMARY KEY,
            bounced INTEGER NOT NULL DEFAULT 0,
            unsubscribed INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def _mark_bounced_sync(email: str) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO email_suppressions (email, bounced, unsubscribed)
            VALUES (?, 1, 0)
            ON CONFLICT(email) DO UPDATE SET
              bounced = 1,
              updated_at = CURRENT_TIMESTAMP
            """,
            (email.lower(),),
        )
        conn.commit()
    finally:
        conn.close()


def _mark_unsubscribed_sync(email: str) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT INTO email_suppressions (email, bounced, unsubscribed)
            VALUES (?, 0, 1)
            ON CONFLICT(email) DO UPDATE SET
              unsubscribed = 1,
              updated_at = CURRENT_TIMESTAMP
            """,
            (email.lower(),),
        )
        conn.commit()
    finally:
        conn.close()


def _is_email_suppressed_sync(email: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            """
            SELECT bounced, unsubscribed
            FROM email_suppressions
            WHERE email = ?
            """,
            (email.lower(),),
        ).fetchone()
        if row is None:
            return False
        bounced, unsubscribed = row
        return bool(bounced or unsubscribed)
    finally:
        conn.close()


async def mark_email_bounced(email: str) -> None:
    await asyncio.to_thread(_mark_bounced_sync, email)


async def mark_email_unsubscribed(email: str) -> None:
    await asyncio.to_thread(_mark_unsubscribed_sync, email)


async def is_email_suppressed(email: str) -> bool:
    return await asyncio.to_thread(_is_email_suppressed_sync, email)
