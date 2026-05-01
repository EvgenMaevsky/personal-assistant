import sqlite3
from pathlib import Path

DB_PATH = Path("data/assistant.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                title       TEXT    NOT NULL,
                event_date  DATE    NOT NULL,
                sent_7d     BOOLEAN NOT NULL DEFAULT 0,
                sent_1d     BOOLEAN NOT NULL DEFAULT 0,
                sent_0d     BOOLEAN NOT NULL DEFAULT 0,
                created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                title       TEXT    NOT NULL,
                date        DATE    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'pending',
                created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
