import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Optional

import db


@dataclass
class Reminder:
    id: Optional[int]
    chat_id: int
    title: str
    event_date: date
    sent_7d: bool = False
    sent_1d: bool = False
    sent_0d: bool = False


def add_reminder(chat_id: int, title: str, event_date: date) -> Reminder:
    with db.get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reminders (chat_id, title, event_date) VALUES (?, ?, ?)",
            (chat_id, title, event_date.isoformat()),
        )
        conn.commit()
    return Reminder(id=cursor.lastrowid, chat_id=chat_id, title=title, event_date=event_date)


def list_reminders(chat_id: int) -> list[Reminder]:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE chat_id = ? ORDER BY event_date",
            (chat_id,),
        ).fetchall()
    return [_row_to_reminder(r) for r in rows]


def delete_reminder(chat_id: int, title_fragment: str) -> bool:
    with db.get_connection() as conn:
        result = conn.execute(
            "DELETE FROM reminders WHERE chat_id = ? AND title LIKE ?",
            (chat_id, f"%{title_fragment}%"),
        )
        conn.commit()
    return result.rowcount > 0


def get_due_reminders(today: date) -> list[tuple[Reminder, str]]:
    due = []
    with db.get_connection() as conn:
        rows = conn.execute("SELECT * FROM reminders").fetchall()
    for row in rows:
        r = _row_to_reminder(row)
        delta = (r.event_date - today).days
        if delta == 7 and not r.sent_7d:
            due.append((r, "7d"))
        elif delta == 1 and not r.sent_1d:
            due.append((r, "1d"))
        elif delta == 0 and not r.sent_0d:
            due.append((r, "0d"))
    return due


def mark_reminder_sent(reminder_id: int, label: str) -> None:
    col_map = {"7d": "sent_7d", "1d": "sent_1d", "0d": "sent_0d"}
    if label not in col_map:
        raise ValueError(f"Invalid label: {label!r}")
    with db.get_connection() as conn:
        conn.execute(f"UPDATE reminders SET {col_map[label]} = 1 WHERE id = ?", (reminder_id,))
        conn.commit()


def _row_to_reminder(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        chat_id=row["chat_id"],
        title=row["title"],
        event_date=date.fromisoformat(row["event_date"]),
        sent_7d=bool(row["sent_7d"]),
        sent_1d=bool(row["sent_1d"]),
        sent_0d=bool(row["sent_0d"]),
    )
