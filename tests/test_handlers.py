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
