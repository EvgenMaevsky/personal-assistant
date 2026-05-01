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
            f"Доброго ранку! \U0001f4cb Незавершене:\n{lines}\n\n"
            "Що плануєш на сьогодні? (відповідай списком, кожне завдання з нового рядка)"
        )
    else:
        msg = (
            "Доброго ранку! \U0001f4cb Незавершених завдань немає.\n\n"
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
            text="Кінець дня! Всі завдання виконано. Молодець! \U0001f389",
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
