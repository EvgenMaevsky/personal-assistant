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
    db.init_db()  # called a second time (conftest already called it once)


def test_get_connection_returns_row_factory():
    import db
    with db.get_connection() as conn:
        conn.execute(
            "INSERT INTO tasks (chat_id, title, date, status) VALUES (1, 'x', '2026-05-01', 'pending')"
        )
        row = conn.execute("SELECT * FROM tasks").fetchone()
    assert row["title"] == "x"
