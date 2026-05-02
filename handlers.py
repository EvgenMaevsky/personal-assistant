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
        notify_dates = [d for d in [d7, d1, r.event_date] if d >= today]
        dates_str = ", ".join(d.strftime("%d.%m") for d in notify_dates)
        await update.message.reply_text(
            f"Зрозумів! Нагадаю про {r.title} {dates_str}."
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
