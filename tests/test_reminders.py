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
    all_r = reminders.list_reminders(1)
    assert all_r[0].sent_7d is True
