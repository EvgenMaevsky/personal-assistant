# Telegram Personal Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 24/7 Telegram bot that stores reminders and daily tasks, sends scheduled standups, and understands natural language (Ukrainian/English) via Ollama + voice via Whisper, running for free on Oracle Cloud ARM.

**Architecture:** Single Python process on Oracle Cloud free A1 VM. python-telegram-bot handles Telegram I/O and job scheduling. All data lives in SQLite. Ollama (qwen2.5:3b) parses natural language into JSON intents; faster-whisper transcribes voice to text before passing to the same NLP pipeline.

**Tech Stack:** Python 3.11, python-telegram-bot 20.x, faster-whisper, httpx, pydantic-settings, SQLite, Ollama/qwen2.5:3b, pytest, pytest-asyncio

---

## File Map

| File | Responsibility |
|---|---|
| `config.py` | Loads `.env`, validates all fields at startup |
| `db.py` | SQLite connection, schema init (CREATE TABLE IF NOT EXISTS) |
| `reminders.py` | Reminder CRUD + `get_due_reminders()` + `mark_reminder_sent()` |
| `tasks.py` | Task CRUD + `get_pending_tasks()` (carry-forward) + `complete_tasks_by_indices()` |
| `state.py` | In-memory `dict[chat_id → action]` for multi-turn replies |
| `nlp.py` | Calls Ollama `/api/chat`, returns parsed JSON dict |
| `whisper_stt.py` | Downloads OGA audio, converts via ffmpeg, returns transcribed text |
| `handlers.py` | Routes Telegram messages: checks state → awaiting path or NLP path |
| `scheduler.py` | Registers 3 daily jobs: morning standup, evening check-in, reminder check |
| `bot.py` | Entry point: init DB, build Application, register handlers + jobs, run polling |
| `tests/conftest.py` | Patches DB path per test, resets state, sets env vars so config imports cleanly |
| `tests/test_config.py` | Config validation |
| `tests/test_db.py` | Schema creation, idempotent init |
| `tests/test_reminders.py` | CRUD + due-date logic |
| `tests/test_tasks.py` | CRUD + carry-forward + complete by indices |
| `tests/test_state.py` | Set/get/clear state |
| `tests/test_nlp.py` | Ollama call (mocked httpx) + error path |
| `tests/test_whisper_stt.py` | Transcription (mocked subprocess + model) |
| `tests/test_handlers.py` | Handler routing for awaiting_tasks, awaiting_completion, NLP error |
| `tests/test_scheduler.py` | Morning standup, evening check-in, reminder check messages |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.env.example`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `requirements.txt`**

```
python-telegram-bot[job-queue]==20.7
faster-whisper==1.0.3
pydantic-settings==2.2.1
httpx==0.27.0
pytest==8.1.0
pytest-asyncio==0.23.5
```

- [ ] **Step 2: Write `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
```

- [ ] **Step 3: Write `.env.example`**

```env
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
MORNING_TIME=09:00
EVENING_TIME=18:00
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=small
```

- [ ] **Step 4: Write `tests/conftest.py`**

This file runs before any test. It sets env vars so `config.py` can be imported without a real `.env`, patches `db.DB_PATH` to a temp file per test, and resets `state` between tests.

```python
import os
import pytest

# Must be set before any module importing config is loaded.
os.environ.setdefault("BOT_TOKEN", "test_token")
os.environ.setdefault("CHAT_ID", "12345")
os.environ.setdefault("MORNING_TIME", "09:00")
os.environ.setdefault("EVENING_TIME", "18:00")
os.environ.setdefault("OLLAMA_MODEL", "qwen2.5:3b")
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("WHISPER_MODEL", "small")


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()


@pytest.fixture(autouse=True)
def reset_state():
    import state
    state.clear_all()
    yield
    state.clear_all()
```

- [ ] **Step 5: Install dependencies**

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Expected: all packages install without error.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini .env.example tests/conftest.py
git commit -m "chore: project scaffold — deps, pytest config, test fixtures"
```

---

## Task 2: config.py

**Files:**
- Create: `config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import os
import pytest


def test_config_reads_env_vars():
    from config import Config
    cfg = Config()
    assert cfg.bot_token == "test_token"
    assert cfg.chat_id == 12345
    assert cfg.morning_time == "09:00"
    assert cfg.evening_time == "18:00"
    assert cfg.ollama_model == "qwen2.5:3b"
    assert cfg.whisper_model == "small"


def test_invalid_morning_time_raises(monkeypatch):
    monkeypatch.setenv("MORNING_TIME", "25:00")
    with pytest.raises(Exception):
        from importlib import reload
        import config as cfg_mod
        reload(cfg_mod)
        cfg_mod.Config()


def test_invalid_evening_time_raises(monkeypatch):
    monkeypatch.setenv("EVENING_TIME", "18:99")
    with pytest.raises(Exception):
        from importlib import reload
        import config as cfg_mod
        reload(cfg_mod)
        cfg_mod.Config()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write `config.py`**

```python
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    bot_token: str
    chat_id: int
    morning_time: str = "09:00"
    evening_time: str = "18:00"
    ollama_model: str = "qwen2.5:3b"
    ollama_host: str = "http://localhost:11434"
    whisper_model: str = "small"

    @field_validator("morning_time", "evening_time")
    @classmethod
    def valid_time(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError(f"Time must be HH:MM, got: {v}")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"Time out of range: {v}")
        return v

    model_config = {"env_file": ".env"}


config = Config()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config loading and validation from .env"
```

---

## Task 3: db.py

**Files:**
- Create: `db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py


def test_init_db_creates_reminders_table():
    import db
    with db.get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "reminders" in tables


def test_init_db_creates_tasks_table():
    import db
    with db.get_connection() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert "tasks" in tables


def test_init_db_is_idempotent():
    import db
    db.init_db()  # called a second time by this test (conftest already called it once)
    # should not raise


def test_get_connection_returns_row_factory():
    import db
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (chat_id, title, date, status) VALUES (1, 'x', '2026-05-01', 'pending')"
        )
        row = conn.execute("SELECT * FROM tasks").fetchone()
    assert row["title"] == "x"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Write `db.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: SQLite connection and schema init"
```

---

## Task 4: reminders.py

**Files:**
- Create: `reminders.py`
- Create: `tests/test_reminders.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_reminders.py
from datetime import date
import reminders


def test_add_reminder_returns_reminder():
    r = reminders.add_reminder(1, "мамин день народження", date(2026, 5, 15))
    assert r.id is not None
    assert r.title == "мамин день народження"
    assert r.event_date == date(2026, 5, 15)
    assert r.sent_7d is False


def test_list_reminders_returns_all_for_chat():
    reminders.add_reminder(1, "birthday", date(2026, 6, 1))
    reminders.add_reminder(1, "dentist", date(2026, 6, 10))
    reminders.add_reminder(2, "other chat", date(2026, 6, 5))
    result = reminders.list_reminders(1)
    assert len(result) == 2
    assert all(r.chat_id == 1 for r in result)


def test_list_reminders_ordered_by_date():
    reminders.add_reminder(1, "later", date(2026, 7, 1))
    reminders.add_reminder(1, "sooner", date(2026, 6, 1))
    result = reminders.list_reminders(1)
    assert result[0].title == "sooner"


def test_delete_reminder_by_title_fragment():
    reminders.add_reminder(1, "прийом до лікаря", date(2026, 6, 3))
    deleted = reminders.delete_reminder(1, "лікаря")
    assert deleted is True
    assert reminders.list_reminders(1) == []


def test_delete_reminder_returns_false_if_not_found():
    deleted = reminders.delete_reminder(1, "nonexistent")
    assert deleted is False


def test_get_due_reminders_7d():
    today = date(2026, 5, 1)
    reminders.add_reminder(1, "event", date(2026, 5, 8))  # 7 days away
    due = reminders.get_due_reminders(today)
    assert len(due) == 1
    assert due[0][1] == "7d"


def test_get_due_reminders_1d():
    today = date(2026, 5, 1)
    reminders.add_reminder(1, "event", date(2026, 5, 2))  # 1 day away
    due = reminders.get_due_reminders(today)
    assert len(due) == 1
    assert due[0][1] == "1d"


def test_get_due_reminders_0d():
    today = date(2026, 5, 1)
    reminders.add_reminder(1, "event", date(2026, 5, 1))  # today
    due = reminders.get_due_reminders(today)
    assert len(due) == 1
    assert due[0][1] == "0d"


def test_get_due_reminders_skips_already_sent():
    today = date(2026, 5, 1)
    r = reminders.add_reminder(1, "event", date(2026, 5, 8))
    reminders.mark_reminder_sent(r.id, "7d")
    due = reminders.get_due_reminders(today)
    assert due == []


def test_mark_reminder_sent():
    r = reminders.add_reminder(1, "event", date(2026, 5, 8))
    reminders.mark_reminder_sent(r.id, "7d")
    # Reload from DB
    all_r = reminders.list_reminders(1)
    assert all_r[0].sent_7d is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_reminders.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'reminders'`

- [ ] **Step 3: Write `reminders.py`**

```python
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
    col = {"7d": "sent_7d", "1d": "sent_1d", "0d": "sent_0d"}[label]
    with db.get_connection() as conn:
        conn.execute(f"UPDATE reminders SET {col} = 1 WHERE id = ?", (reminder_id,))
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_reminders.py -v
```

Expected: 10 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add reminders.py tests/test_reminders.py
git commit -m "feat: reminders CRUD and due-date logic"
```

---

## Task 5: tasks.py

**Files:**
- Create: `tasks.py`
- Create: `tests/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tasks.py
from datetime import date
import tasks


def test_add_tasks_returns_task_list():
    result = tasks.add_tasks(1, ["fix bug", "write docs"], date(2026, 5, 4))
    assert len(result) == 2
    assert result[0].title == "fix bug"
    assert result[0].status == "pending"
    assert result[1].title == "write docs"


def test_get_pending_tasks_returns_only_pending():
    today = date(2026, 5, 4)
    tasks.add_tasks(1, ["task a", "task b"], today)
    result = tasks.get_pending_tasks(1, today)
    assert len(result) == 2


def test_get_pending_tasks_carry_forward():
    yesterday = date(2026, 5, 3)
    today = date(2026, 5, 4)
    tasks.add_tasks(1, ["old task"], yesterday)
    result = tasks.get_pending_tasks(1, today)
    assert len(result) == 1
    assert result[0].title == "old task"


def test_get_pending_tasks_excludes_done():
    today = date(2026, 5, 4)
    created = tasks.add_tasks(1, ["task a", "task b"], today)
    tasks.complete_tasks_by_indices(1, today, [1])
    result = tasks.get_pending_tasks(1, today)
    assert len(result) == 1
    assert result[0].title == "task b"


def test_get_tasks_for_date_returns_all_statuses():
    today = date(2026, 5, 4)
    tasks.add_tasks(1, ["a", "b"], today)
    tasks.complete_tasks_by_indices(1, today, [1])
    result = tasks.get_tasks_for_date(1, today)
    assert len(result) == 2
    statuses = {t.status for t in result}
    assert statuses == {"pending", "done"}


def test_complete_tasks_by_indices_marks_done():
    today = date(2026, 5, 4)
    tasks.add_tasks(1, ["first", "second", "third"], today)
    count = tasks.complete_tasks_by_indices(1, today, [1, 3])
    assert count == 2
    pending = tasks.get_pending_tasks(1, today)
    assert len(pending) == 1
    assert pending[0].title == "second"


def test_complete_tasks_by_indices_ignores_out_of_range():
    today = date(2026, 5, 4)
    tasks.add_tasks(1, ["only one"], today)
    count = tasks.complete_tasks_by_indices(1, today, [5, 99])
    assert count == 0


def test_complete_tasks_uses_pending_list_for_indexing():
    today = date(2026, 5, 4)
    tasks.add_tasks(1, ["a", "b", "c"], today)
    tasks.complete_tasks_by_indices(1, today, [1])  # marks "a" done
    # Now pending = ["b", "c"]. Index 1 should now be "b".
    count = tasks.complete_tasks_by_indices(1, today, [1])
    assert count == 1
    pending = tasks.get_pending_tasks(1, today)
    assert len(pending) == 1
    assert pending[0].title == "c"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tasks.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'tasks'`

- [ ] **Step 3: Write `tasks.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tasks.py -v
```

Expected: 8 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add tasks.py tests/test_tasks.py
git commit -m "feat: tasks CRUD, carry-forward, and completion by index"
```

---

## Task 6: state.py

**Files:**
- Create: `state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_state.py
import state


def test_set_and_get_action():
    state.set_action(123, "awaiting_tasks")
    assert state.get_action(123) == "awaiting_tasks"


def test_clear_action_removes_entry():
    state.set_action(123, "awaiting_tasks")
    state.clear_action(123)
    assert state.get_action(123) is None


def test_unknown_chat_returns_none():
    assert state.get_action(999999) is None


def test_overwrite_action():
    state.set_action(1, "awaiting_tasks")
    state.set_action(1, "awaiting_completion")
    assert state.get_action(1) == "awaiting_completion"


def test_clear_all_empties_dict():
    state.set_action(1, "awaiting_tasks")
    state.set_action(2, "awaiting_completion")
    state.clear_all()
    assert state.get_action(1) is None
    assert state.get_action(2) is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_state.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Write `state.py`**

```python
_state: dict[int, str] = {}


def set_action(chat_id: int, action: str) -> None:
    _state[chat_id] = action


def get_action(chat_id: int) -> str | None:
    return _state.get(chat_id)


def clear_action(chat_id: int) -> None:
    _state.pop(chat_id, None)


def clear_all() -> None:
    _state.clear()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_state.py -v
```

Expected: 5 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "feat: in-memory conversation state for multi-turn replies"
```

---

## Task 7: nlp.py

**Files:**
- Create: `nlp.py`
- Create: `tests/test_nlp.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_nlp.py
import json
import pytest
from unittest.mock import MagicMock, patch


def _make_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"message": {"content": json.dumps(payload)}}
    mock.raise_for_status = MagicMock()
    return mock


@patch("nlp.httpx.post")
def test_parse_add_reminder(mock_post):
    mock_post.return_value = _make_response({
        "intent": "add_reminder",
        "title": "день народження мами",
        "date": "2026-05-15",
        "tasks": [],
        "task_indices": [],
    })
    from nlp import parse_message
    result = parse_message("Нагадай про день народження мами 15 травня", "2026-05-01")
    assert result["intent"] == "add_reminder"
    assert result["title"] == "день народження мами"
    assert result["date"] == "2026-05-15"


@patch("nlp.httpx.post")
def test_parse_add_tasks(mock_post):
    mock_post.return_value = _make_response({
        "intent": "add_tasks",
        "title": "",
        "date": "",
        "tasks": ["фіксити баг", "дзвонити клієнту"],
        "task_indices": [],
    })
    from nlp import parse_message
    result = parse_message("Сьогодні буду: фіксити баг, дзвонити клієнту", "2026-05-01")
    assert result["intent"] == "add_tasks"
    assert "фіксити баг" in result["tasks"]


@patch("nlp.httpx.post")
def test_parse_complete_tasks(mock_post):
    mock_post.return_value = _make_response({
        "intent": "complete_tasks",
        "title": "",
        "date": "",
        "tasks": [],
        "task_indices": [1, 2],
    })
    from nlp import parse_message
    result = parse_message("Зробив перше і друге", "2026-05-01")
    assert result["intent"] == "complete_tasks"
    assert result["task_indices"] == [1, 2]


@patch("nlp.httpx.post")
def test_ollama_request_error_raises_runtime_error(mock_post):
    import httpx
    mock_post.side_effect = httpx.RequestError("connection refused")
    from nlp import parse_message
    with pytest.raises(RuntimeError, match="Ollama error"):
        parse_message("test", "2026-05-01")


@patch("nlp.httpx.post")
def test_invalid_json_response_raises_runtime_error(mock_post):
    mock = MagicMock()
    mock.json.return_value = {"message": {"content": "not json {"}}
    mock.raise_for_status = MagicMock()
    mock_post.return_value = mock
    from nlp import parse_message
    with pytest.raises(RuntimeError, match="Ollama error"):
        parse_message("test", "2026-05-01")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_nlp.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'nlp'`

- [ ] **Step 3: Write `nlp.py`**

```python
import json
import httpx
from config import config

_SYSTEM_PROMPT = """You are a JSON extraction assistant for a personal assistant bot.
The user speaks Ukrainian or English. Extract the intent and entities from their message.

Return ONLY valid JSON in exactly this format:
{
  "intent": "<intent>",
  "title": "<event or task title, or empty string>",
  "date": "<ISO date YYYY-MM-DD, or empty string>",
  "tasks": ["<task 1>", "<task 2>"],
  "task_indices": [1, 2]
}

Valid intents:
- add_reminder: user wants to remember a date-based event (put event name in title, date in date)
- list_reminders: user asks to see their reminders
- delete_reminder: user wants to remove a reminder (put event name in title)
- add_tasks: user lists work tasks (put them in tasks array)
- complete_tasks: user says which tasks they finished (put 1-based numbers in task_indices)
- list_tasks: user asks what tasks they have today
- unknown: anything else

Today is {today}. Resolve relative dates like "tomorrow" or "наступного понеділка" to ISO format."""


def parse_message(text: str, today: str) -> dict:
    """Call Ollama and return parsed intent dict. Raises RuntimeError on any failure."""
    payload = {
        "model": config.ollama_model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT.format(today=today)},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "format": "json",
    }
    try:
        response = httpx.post(
            f"{config.ollama_host}/api/chat",
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
        return json.loads(content)
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError(f"Ollama error: {exc}") from exc
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_nlp.py -v
```

Expected: 5 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add nlp.py tests/test_nlp.py
git commit -m "feat: Ollama NLP intent extraction with Ukrainian support"
```

---

## Task 8: whisper_stt.py

**Files:**
- Create: `whisper_stt.py`
- Create: `tests/test_whisper_stt.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_whisper_stt.py
import subprocess
import pytest
from unittest.mock import MagicMock, patch


@patch("whisper_stt.subprocess.run")
@patch("whisper_stt._get_model")
def test_transcribe_returns_joined_text(mock_get_model, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    seg1 = MagicMock()
    seg1.text = " нагадай"
    seg2 = MagicMock()
    seg2.text = " про зустріч "
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([seg1, seg2], MagicMock())
    mock_get_model.return_value = mock_model

    from whisper_stt import transcribe
    result = transcribe(b"fake_audio")
    assert result == "нагадай про зустріч"


@patch("whisper_stt.subprocess.run")
def test_transcribe_raises_on_ffmpeg_failure(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr=b"error")

    from whisper_stt import transcribe
    with pytest.raises(subprocess.CalledProcessError):
        transcribe(b"bad_audio")


@patch("whisper_stt.subprocess.run")
@patch("whisper_stt._get_model")
def test_transcribe_strips_whitespace(mock_get_model, mock_run):
    mock_run.return_value = MagicMock(returncode=0)
    seg = MagicMock()
    seg.text = "  текст  "
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([seg], MagicMock())
    mock_get_model.return_value = mock_model

    from whisper_stt import transcribe
    result = transcribe(b"audio")
    assert result == "текст"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_whisper_stt.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'whisper_stt'`

- [ ] **Step 3: Write `whisper_stt.py`**

```python
import os
import subprocess
import tempfile
from faster_whisper import WhisperModel
from config import config

_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = WhisperModel(config.whisper_model, device="cpu", compute_type="int8")
    return _model


def transcribe(ogg_bytes: bytes) -> str:
    """Transcribe OGA voice bytes to text. Raises subprocess.CalledProcessError if ffmpeg fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        oga_path = os.path.join(tmpdir, "audio.oga")
        wav_path = os.path.join(tmpdir, "audio.wav")
        with open(oga_path, "wb") as f:
            f.write(ogg_bytes)
        subprocess.run(
            ["ffmpeg", "-i", oga_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            capture_output=True,
        )
        model = _get_model()
        segments, _ = model.transcribe(wav_path, language="uk")
        return " ".join(seg.text.strip() for seg in segments).strip()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_whisper_stt.py -v
```

Expected: 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add whisper_stt.py tests/test_whisper_stt.py
git commit -m "feat: voice transcription via faster-whisper and ffmpeg"
```

---

## Task 9: handlers.py

**Files:**
- Create: `handlers.py`
- Create: `tests/test_handlers.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_handlers.py
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import state
import tasks


@pytest.fixture
def update():
    u = MagicMock()
    u.effective_chat.id = 42
    u.message.reply_text = AsyncMock()
    return u


@pytest.fixture
def ctx():
    return MagicMock()


async def test_awaiting_tasks_saves_and_clears_state(update, ctx):
    state.set_action(42, "awaiting_tasks")
    update.message.text = "фіксити баг\nдзвонити клієнту"

    from handlers import handle_text
    with patch("handlers.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 4)
        await handle_text(update, ctx)

    update.message.reply_text.assert_called_once()
    reply = update.message.reply_text.call_args[0][0]
    assert "2 завдання" in reply
    assert state.get_action(42) is None


async def test_awaiting_tasks_ignores_blank_lines(update, ctx):
    state.set_action(42, "awaiting_tasks")
    update.message.text = "перша задача\n\n  \nдруга задача"

    from handlers import handle_text
    with patch("handlers.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 4)
        await handle_text(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "2 завдання" in reply


async def test_awaiting_completion_marks_done(update, ctx):
    today = date(2026, 5, 4)
    tasks.add_tasks(42, ["a", "b"], today)
    state.set_action(42, "awaiting_completion")
    update.message.text = "1"

    from handlers import handle_text
    with patch("handlers.date") as mock_date:
        mock_date.today.return_value = today
        await handle_text(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "1 виконано" in reply
    assert state.get_action(42) is None


@patch("handlers.nlp.parse_message")
async def test_nlp_error_sends_error_message(mock_parse, update, ctx):
    mock_parse.side_effect = RuntimeError("Ollama unreachable")
    update.message.text = "щось написав"

    from handlers import handle_text
    with patch("handlers.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 4)
        await handle_text(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "Не вдалось" in reply


@patch("handlers.nlp.parse_message")
async def test_unknown_intent_sends_fallback(mock_parse, update, ctx):
    mock_parse.return_value = {"intent": "unknown", "title": "", "date": "", "tasks": [], "task_indices": []}
    update.message.text = "абракадабра"

    from handlers import handle_text
    with patch("handlers.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 4)
        await handle_text(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "Не зрозумів" in reply


@patch("handlers.nlp.parse_message")
async def test_add_reminder_intent(mock_parse, update, ctx):
    mock_parse.return_value = {
        "intent": "add_reminder",
        "title": "зустріч",
        "date": "2026-06-10",
        "tasks": [],
        "task_indices": [],
    }
    update.message.text = "нагадай про зустріч 10 червня"

    from handlers import handle_text
    with patch("handlers.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 4)
        mock_date.fromisoformat = date.fromisoformat
        await handle_text(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "зустріч" in reply
    assert "Зрозумів" in reply


async def test_voice_transcription_failure_sends_error(update, ctx):
    import subprocess
    ctx.bot.get_file = AsyncMock()
    ctx.bot.get_file.return_value.download_as_bytearray = AsyncMock(return_value=bytearray(b"audio"))

    from handlers import handle_voice
    with patch("handlers.whisper_stt.transcribe", side_effect=subprocess.CalledProcessError(1, "ffmpeg")):
        await handle_voice(update, ctx)

    reply = update.message.reply_text.call_args[0][0]
    assert "голосове" in reply
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_handlers.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'handlers'`

- [ ] **Step 3: Write `handlers.py`**

```python
from datetime import date, timedelta
from telegram import Update
from telegram.ext import ContextTypes

import nlp
import reminders
import state
import tasks
import whisper_stt


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    today = date.today()

    pending_action = state.get_action(chat_id)

    if pending_action == "awaiting_tasks":
        state.clear_action(chat_id)
        titles = [line.strip() for line in text.splitlines() if line.strip()]
        tasks.add_tasks(chat_id, titles, today)
        await update.message.reply_text(f"Збережено! {len(titles)} завдання на сьогодні. Вдачі!")
        return

    if pending_action == "awaiting_completion":
        state.clear_action(chat_id)
        indices = [int(x) for x in text.split() if x.isdigit()]
        done = tasks.complete_tasks_by_indices(chat_id, today, indices)
        remaining = len(tasks.get_pending_tasks(chat_id, today))
        await update.message.reply_text(
            f"Чудово! {done} виконано, {remaining} переноситься на завтра."
        )
        return

    await _handle_nlp(update, text, today)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    voice_file = await context.bot.get_file(update.message.voice.file_id)
    ogg_bytes = await voice_file.download_as_bytearray()

    try:
        text = whisper_stt.transcribe(bytes(ogg_bytes))
    except Exception:
        await update.message.reply_text(
            "Не вдалось розпізнати голосове повідомлення. Спробуй написати текстом."
        )
        return

    await update.message.reply_text(f"🎤 Розпізнано: {text}")
    await _handle_nlp(update, text, date.today())


async def _handle_nlp(update: Update, text: str, today: date) -> None:
    chat_id = update.effective_chat.id

    try:
        parsed = nlp.parse_message(text, today.isoformat())
    except RuntimeError:
        await update.message.reply_text("Не вдалось розпізнати повідомлення. Спробуй ще раз.")
        return

    intent = parsed.get("intent", "unknown")

    if intent == "add_reminder":
        event_date = date.fromisoformat(parsed["date"])
        r = reminders.add_reminder(chat_id, parsed["title"], event_date)
        d7 = r.event_date - timedelta(days=7)
        d1 = r.event_date - timedelta(days=1)
        await update.message.reply_text(
            f"Зрозумів! Нагадаю про {r.title} "
            f"{d7.strftime('%d.%m')}, {d1.strftime('%d.%m')} та {r.event_date.strftime('%d.%m')}."
        )

    elif intent == "list_reminders":
        all_reminders = reminders.list_reminders(chat_id)
        if not all_reminders:
            await update.message.reply_text("Нагадувань немає.")
            return
        lines = "\n".join(f"• {r.event_date.strftime('%d.%m')} — {r.title}" for r in all_reminders)
        await update.message.reply_text(f"📅 Майбутні нагадування:\n{lines}")

    elif intent == "delete_reminder":
        deleted = reminders.delete_reminder(chat_id, parsed["title"])
        if deleted:
            await update.message.reply_text(f"Видалено нагадування: {parsed['title']}.")
        else:
            await update.message.reply_text("Нагадування не знайдено.")

    elif intent == "add_tasks":
        task_titles = parsed.get("tasks", [])
        if not task_titles:
            await update.message.reply_text("Не розпізнав завдань. Спробуй ще раз.")
            return
        tasks.add_tasks(chat_id, task_titles, today)
        await update.message.reply_text(f"Збережено! {len(task_titles)} завдання. Вдачі!")

    elif intent == "complete_tasks":
        indices = parsed.get("task_indices", [])
        done = tasks.complete_tasks_by_indices(chat_id, today, indices)
        remaining = len(tasks.get_pending_tasks(chat_id, today))
        await update.message.reply_text(
            f"Чудово! {done} виконано, {remaining} переноситься на завтра."
        )

    elif intent == "list_tasks":
        today_tasks = [t for t in tasks.get_tasks_for_date(chat_id, today) if t.status == "pending"]
        if not today_tasks:
            await update.message.reply_text("Завдань на сьогодні немає.")
            return
        lines = "\n".join(f"{i + 1}. {t.title}" for i, t in enumerate(today_tasks))
        await update.message.reply_text(f"📋 Завдання на сьогодні:\n{lines}")

    else:
        await update.message.reply_text("Не зрозумів. Спробуй переформулювати.")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_handlers.py -v
```

Expected: 8 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add handlers.py tests/test_handlers.py
git commit -m "feat: Telegram message handlers — text, voice, NLP routing"
```

---

## Task 10: scheduler.py

**Files:**
- Create: `scheduler.py`
- Create: `tests/test_scheduler.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scheduler.py
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import tasks
import state


@pytest.fixture
def ctx():
    c = MagicMock()
    c.bot.send_message = AsyncMock()
    return c


async def test_morning_standup_no_pending_no_carry(ctx):
    from scheduler import _morning_standup
    with patch("scheduler.date") as mock_date, \
         patch("scheduler.config") as mock_cfg:
        mock_date.today.return_value = date(2026, 5, 4)
        mock_cfg.chat_id = 42
        await _morning_standup(ctx)

    call_text = ctx.bot.send_message.call_args[1]["text"]
    assert "Незавершених завдань немає" in call_text
    assert state.get_action(42) == "awaiting_tasks"


async def test_morning_standup_shows_pending_tasks(ctx):
    today = date(2026, 5, 4)
    yesterday = date(2026, 5, 3)
    tasks.add_tasks(42, ["стара задача"], yesterday)

    from scheduler import _morning_standup
    with patch("scheduler.date") as mock_date, \
         patch("scheduler.config") as mock_cfg:
        mock_date.today.return_value = today
        mock_cfg.chat_id = 42
        await _morning_standup(ctx)

    call_text = ctx.bot.send_message.call_args[1]["text"]
    assert "стара задача" in call_text


async def test_evening_checkin_all_done_sends_congrats(ctx):
    today = date(2026, 5, 4)
    created = tasks.add_tasks(42, ["task"], today)
    tasks.complete_tasks_by_indices(42, today, [1])

    from scheduler import _evening_checkin
    with patch("scheduler.date") as mock_date, \
         patch("scheduler.config") as mock_cfg:
        mock_date.today.return_value = today
        mock_cfg.chat_id = 42
        await _evening_checkin(ctx)

    call_text = ctx.bot.send_message.call_args[1]["text"]
    assert "Всі завдання виконано" in call_text
    assert state.get_action(42) != "awaiting_completion"


async def test_evening_checkin_shows_pending_and_sets_state(ctx):
    today = date(2026, 5, 4)
    tasks.add_tasks(42, ["pending task"], today)

    from scheduler import _evening_checkin
    with patch("scheduler.date") as mock_date, \
         patch("scheduler.config") as mock_cfg:
        mock_date.today.return_value = today
        mock_cfg.chat_id = 42
        await _evening_checkin(ctx)

    call_text = ctx.bot.send_message.call_args[1]["text"]
    assert "pending task" in call_text
    assert state.get_action(42) == "awaiting_completion"


async def test_check_reminders_sends_7d_message(ctx):
    import reminders
    from datetime import timedelta
    today = date(2026, 5, 1)
    reminders.add_reminder(42, "birthday", today + timedelta(days=7))

    from scheduler import _check_reminders
    with patch("scheduler.date") as mock_date:
        mock_date.today.return_value = today
        await _check_reminders(ctx)

    call_text = ctx.bot.send_message.call_args[1]["text"]
    assert "7 днів" in call_text
    assert "birthday" in call_text


async def test_check_reminders_marks_sent(ctx):
    import reminders
    from datetime import timedelta
    today = date(2026, 5, 1)
    r = reminders.add_reminder(42, "event", today + timedelta(days=7))

    from scheduler import _check_reminders
    with patch("scheduler.date") as mock_date:
        mock_date.today.return_value = today
        await _check_reminders(ctx)

    updated = reminders.list_reminders(42)
    assert updated[0].sent_7d is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_scheduler.py -v
```

Expected: `FAILED` — `ModuleNotFoundError: No module named 'scheduler'`

- [ ] **Step 3: Write `scheduler.py`**

```python
from datetime import date, time
from telegram.ext import Application

import reminders
import state
import tasks
from config import config


def register_jobs(app: Application) -> None:
    morning_h, morning_m = map(int, config.morning_time.split(":"))
    evening_h, evening_m = map(int, config.evening_time.split(":"))

    app.job_queue.run_daily(
        _morning_standup,
        time=time(morning_h, morning_m),
        days=(0, 1, 2, 3, 4),
    )
    app.job_queue.run_daily(
        _evening_checkin,
        time=time(evening_h, evening_m),
        days=(0, 1, 2, 3, 4),
    )
    app.job_queue.run_daily(
        _check_reminders,
        time=time(morning_h, morning_m),
    )


async def _morning_standup(context) -> None:
    chat_id = config.chat_id
    today = date.today()
    pending = tasks.get_pending_tasks(chat_id, today)

    if pending:
        lines = "\n".join(f"- {t.title}" for t in pending)
        msg = (
            f"Доброго ранку! 📋 Незавершене:\n{lines}\n\n"
            "Що плануєш на сьогодні? (відповідай списком, кожне завдання з нового рядка)"
        )
    else:
        msg = (
            "Доброго ранку! 📋 Незавершених завдань немає.\n\n"
            "Що плануєш на сьогодні? (відповідай списком, кожне завдання з нового рядка)"
        )

    state.set_action(chat_id, "awaiting_tasks")
    await context.bot.send_message(chat_id=chat_id, text=msg)


async def _evening_checkin(context) -> None:
    chat_id = config.chat_id
    today = date.today()
    pending_today = [t for t in tasks.get_tasks_for_date(chat_id, today) if t.status == "pending"]

    if not pending_today:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Кінець дня! Всі завдання виконано. Молодець! 🎉",
        )
        return

    lines = "\n".join(f"{i + 1}. {t.title}" for i, t in enumerate(pending_today))
    msg = (
        f"Кінець дня! Що вдалось зробити?\n{lines}\n\n"
        "Надішли номери виконаних завдань (наприклад: '1 2')"
    )
    state.set_action(chat_id, "awaiting_completion")
    await context.bot.send_message(chat_id=chat_id, text=msg)


async def _check_reminders(context) -> None:
    today = date.today()
    due = reminders.get_due_reminders(today)
    for reminder, label in due:
        if label == "7d":
            msg = f"⏰ Нагадування: через 7 днів — {reminder.title} ({reminder.event_date.strftime('%d.%m')})"
        elif label == "1d":
            msg = f"⏰ Нагадування: завтра — {reminder.title} ({reminder.event_date.strftime('%d.%m')})"
        else:
            msg = f"⏰ Сьогодні — {reminder.title}!"
        await context.bot.send_message(chat_id=reminder.chat_id, text=msg)
        reminders.mark_reminder_sent(reminder.id, label)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scheduler.py -v
```

Expected: 6 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: scheduler — morning standup, evening check-in, reminder checks"
```

---

## Task 11: bot.py (Entry Point)

**Files:**
- Create: `bot.py`

No unit tests for the entry point — it just wires existing components. Manual smoke test instructions are provided in Step 3.

- [ ] **Step 1: Write `bot.py`**

```python
import logging
from telegram.ext import Application, MessageHandler, filters

import db
import handlers
import scheduler
from config import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler(),
    ],
)


def main() -> None:
    db.init_db()
    app = Application.builder().token(config.bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handlers.handle_voice))
    scheduler.register_jobs(app)
    logging.info("Bot started. Polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full test suite**

```bash
pytest -v
```

Expected: all tests `PASSED`, 0 failures.

- [ ] **Step 3: Smoke test locally (requires a real Telegram bot token)**

Get a bot token from [@BotFather](https://t.me/BotFather) on Telegram. Find your chat ID by messaging [@userinfobot](https://t.me/userinfobot).

```bash
cp .env.example .env
# Edit .env: set BOT_TOKEN and CHAT_ID to your real values
# Set OLLAMA_HOST=http://localhost:11434 if running Ollama locally for the smoke test
python bot.py
```

Open Telegram and send: `Нагадай про тест 15 червня`

Expected in terminal: `Bot started. Polling...` and bot replies in Telegram with confirmation.

Press `Ctrl+C` to stop.

- [ ] **Step 4: Commit**

```bash
git add bot.py
git commit -m "feat: bot entry point — wires all components together"
```

---

## Task 12: Oracle Cloud VM Deployment

**Files:**
- Create: `deploy/setup.sh`

This task provisions the Oracle A1 free tier VM and runs the bot as a systemd service that starts on boot and auto-restarts on failure.

- [ ] **Step 1: Create Oracle Cloud A1 instance**

1. Log in at [cloud.oracle.com](https://cloud.oracle.com)
2. Go to **Compute → Instances → Create Instance**
3. Change shape to **VM.Standard.A1.Flex** (Ampere ARM) — set 4 OCPUs, 24 GB RAM
4. Image: **Ubuntu 22.04**
5. Generate an SSH key pair and download the private key
6. Click **Create**
7. Note the public IP address

- [ ] **Step 2: SSH into the VM and install system dependencies**

```bash
ssh -i ~/path/to/private_key ubuntu@<YOUR_VM_IP>

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git ffmpeg
```

Expected: all packages install without error. Verify: `ffmpeg -version`

- [ ] **Step 3: Install Ollama and pull the model**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

Expected: model downloads (~2 GB). Verify:
```bash
ollama run qwen2.5:3b "say ok"
```
Expected: model responds with some text. Press Ctrl+D to exit.

- [ ] **Step 4: Clone the repo and set up the Python environment**

```bash
git clone <YOUR_REPO_URL> ~/personal-assistant
cd ~/personal-assistant
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Expected: all packages install. Note: `faster-whisper` will download ~500 MB of ARM-compatible wheels.

- [ ] **Step 5: Configure `.env`**

```bash
cp .env.example .env
nano .env
```

Set these values:
```env
BOT_TOKEN=<your bot token from BotFather>
CHAT_ID=<your Telegram chat ID from userinfobot>
MORNING_TIME=09:00
EVENING_TIME=18:00
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=small
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

- [ ] **Step 6: Write `deploy/setup.sh` and create the systemd service**

```bash
mkdir -p deploy
```

```bash
# deploy/setup.sh — run once on the VM after .env is configured
sudo tee /etc/systemd/system/personal-assistant.service > /dev/null <<EOF
[Unit]
Description=Personal Assistant Telegram Bot
After=network.target ollama.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/personal-assistant
Environment=PATH=/home/ubuntu/personal-assistant/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ubuntu/personal-assistant/venv/bin/python bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable personal-assistant
sudo systemctl start personal-assistant
```

Run it:
```bash
bash deploy/setup.sh
```

- [ ] **Step 7: Verify the service is running**

```bash
sudo systemctl status personal-assistant
```

Expected output contains `Active: active (running)`.

Check logs:
```bash
tail -f ~/personal-assistant/bot.log
```

Expected: `Bot started. Polling...`

- [ ] **Step 8: Send a smoke test message**

In Telegram, send your bot: `Привіт, покажи мої нагадування`

Expected bot reply: `Нагадувань немає.`

- [ ] **Step 9: Commit setup script**

Back on your local machine:
```bash
git add deploy/setup.sh
git commit -m "chore: Oracle VM deployment script and systemd service"
```

---

## Final: Run Full Test Suite

- [ ] **Run all tests**

```bash
pytest -v
```

Expected: all tests `PASSED`.

- [ ] **Check test coverage** (optional but useful)

```bash
pip install pytest-cov
pytest --cov=. --cov-report=term-missing --ignore=tests
```

Review any uncovered branches — the most important are error paths in `handlers.py`.
