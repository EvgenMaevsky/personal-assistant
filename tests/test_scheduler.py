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


async def test_morning_standup_no_pending(ctx):
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
    tasks.add_tasks(42, ["task"], today)
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
