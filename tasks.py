import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Optional

import db


@dataclass
class Task:
    id: Optional[int]
    chat_id: int
    title: str
    date: date
    status: str


def add_tasks(chat_id: int, titles: list[str], for_date: date) -> list[Task]:
    result = []
    with db.get_connection() as conn:
        for title in titles:
            cursor = conn.execute(
                "INSERT INTO tasks (chat_id, title, date, status) VALUES (?, ?, ?, 'pending')",
                (chat_id, title, for_date.isoformat()),
            )
            result.append(Task(id=cursor.lastrowid, chat_id=chat_id, title=title, date=for_date, status="pending"))
        conn.commit()
    return result


def get_pending_tasks(chat_id: int, up_to_date: date) -> list[Task]:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE chat_id = ? AND date <= ? AND status = 'pending' ORDER BY date, id",
            (chat_id, up_to_date.isoformat()),
        ).fetchall()
    return [_row_to_task(r) for r in rows]


def get_tasks_for_date(chat_id: int, for_date: date) -> list[Task]:
    with db.get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE chat_id = ? AND date = ? ORDER BY id",
            (chat_id, for_date.isoformat()),
        ).fetchall()
    return [_row_to_task(r) for r in rows]


def complete_tasks_by_indices(chat_id: int, for_date: date, indices: list[int]) -> int:
    pending = [t for t in get_tasks_for_date(chat_id, for_date) if t.status == "pending"]
    marked = 0
    with db.get_connection() as conn:
        for i in indices:
            if 1 <= i <= len(pending):
                conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (pending[i - 1].id,))
                marked += 1
        conn.commit()
    return marked


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        chat_id=row["chat_id"],
        title=row["title"],
        date=date.fromisoformat(row["date"]),
        status=row["status"],
    )
