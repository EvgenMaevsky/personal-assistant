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
    tasks.add_tasks(1, ["task a", "task b"], today)
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
    # Now pending = ["b", "c"]. Index 1 should be "b".
    count = tasks.complete_tasks_by_indices(1, today, [1])
    assert count == 1
    pending = tasks.get_pending_tasks(1, today)
    assert len(pending) == 1
    assert pending[0].title == "c"
