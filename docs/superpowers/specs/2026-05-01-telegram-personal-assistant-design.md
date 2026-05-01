# Telegram Personal Assistant — Design Spec

**Date:** 2026-05-01  
**Status:** Approved

---

## Goal

A 24/7 Telegram bot that remembers important dates and events via natural language (text or voice), runs daily work standups, and is fully self-hosted on Oracle Cloud free tier with zero ongoing cost.

---

## Architecture

Single Python process on Oracle Cloud free A1 instance (ARM, 4 OCPUs, 24 GB RAM, Ubuntu).

```
User (Telegram) ──► python-telegram-bot ──► handlers.py
                                                 │
                              ┌──────────────────┴──────────────────┐
                         Voice message                         Text message
                              │                                      │
                        whisper_stt.py                               │
                        (faster-whisper)                             │
                              └──────────────────┬──────────────────┘
                                            nlp.py
                                     (Ollama / qwen2.5:3b)
                                            │
                              ┌─────────────┴─────────────┐
                         reminders.py               tasks.py
                              │                           │
                              └────────── db.py ──────────┘
                                         (SQLite)
                                            │
                                      scheduler.py
                              (morning standup, evening check-in,
                               reminder checks)
                                            │
                              python-telegram-bot ──► User
```

---

## Tech Stack

| Component        | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python 3.11+                        |
| Telegram        | python-telegram-bot 20.x (async)    |
| NLP             | Ollama + qwen2.5:3b                 |
| Speech-to-text  | faster-whisper (small model, local) |
| Database        | SQLite (via Python sqlite3)         |
| Scheduling      | python-telegram-bot JobQueue        |
| Hosting         | Oracle Cloud free A1 VM (ARM)       |
| Language support| Ukrainian + English                 |

---

## File Structure

```
personal-assistant/
├── bot.py           # Entry point: initializes bot, registers handlers, starts scheduler
├── handlers.py      # Telegram handlers for text and voice messages
├── nlp.py           # Calls Ollama to extract intent + entities from text
├── whisper_stt.py   # Downloads voice message audio, transcribes with faster-whisper
├── reminders.py     # Reminder CRUD + reminder-due logic
├── tasks.py         # Task CRUD + carry-forward logic
├── scheduler.py     # Scheduled jobs: morning standup, evening check-in, reminder checks
├── db.py            # SQLite connection, schema creation, migrations
├── config.py        # Loads and validates .env configuration
├── requirements.txt
└── .env             # Secrets and configuration (not committed)
```

---

## Data Model

### Table: `reminders`

| Column      | Type     | Description                              |
|-------------|----------|------------------------------------------|
| id          | INTEGER  | Primary key                              |
| chat_id     | INTEGER  | Telegram chat ID                         |
| title       | TEXT     | Event name (e.g. "мамин день народження")|
| event_date  | DATE     | Date of the event                        |
| sent_7d     | BOOLEAN  | Whether the 7-day reminder was sent      |
| sent_1d     | BOOLEAN  | Whether the 1-day reminder was sent      |
| sent_0d     | BOOLEAN  | Whether the day-of reminder was sent     |
| created_at  | DATETIME | Row creation timestamp                   |

### Table: `tasks`

| Column     | Type     | Description                              |
|------------|----------|------------------------------------------|
| id         | INTEGER  | Primary key                              |
| chat_id    | INTEGER  | Telegram chat ID                         |
| title      | TEXT     | Task description                         |
| date       | DATE     | Which working day this task belongs to   |
| status     | TEXT     | `pending` or `done`                      |
| created_at | DATETIME | Row creation timestamp                   |

---

## NLP: Intent Extraction

Ollama (qwen2.5:3b) is called with a structured system prompt instructing it to return JSON. Input can be Ukrainian or English. Output is always JSON.

### Supported intents

| Intent             | Example input (UA)                            |
|--------------------|-----------------------------------------------|
| `add_reminder`     | "Нагадай про день народження мами 15 травня"  |
| `list_reminders`   | "Покажи мої нагадування"                      |
| `delete_reminder`  | "Видали нагадування про день народження мами" |
| `add_tasks`        | "Сьогодні буду: фіксити баг, дзвонити клієнту"|
| `complete_tasks`   | "Зробив перше і друге"                        |
| `list_tasks`       | "Що в мене на сьогодні?"                      |
| `unknown`          | Anything unrecognized                         |

### NLP output schema

```json
{
  "intent": "add_reminder",
  "title": "день народження мами",
  "date": "2026-05-15",
  "task_indices": [],
  "tasks": []
}
```

---

## Voice Support

1. User sends a voice message in Telegram
2. `handlers.py` receives the `Voice` update, calls `whisper_stt.py`
3. `whisper_stt.py` downloads the `.ogg` audio file via Telegram API, converts to WAV, runs `faster-whisper` (small model) transcription with `language="uk"` (Ukrainian) fallback to auto-detect
4. Transcribed text is passed to the same NLP pipeline as typed text
5. Response is sent back as a text message

Transcription latency: ~2–5 seconds on Oracle A1 ARM CPU.

---

## Interaction Flows

### Adding a reminder (text or voice)

```
User: "Нагадай про день народження мами 15 травня"
Bot:  "Зрозумів! Нагадаю про день народження мами 8 травня, 14 травня та 15 травня."
```

### Listing reminders

```
User: "Покажи мої нагадування"
Bot:  "📅 Майбутні нагадування:
       • 15 травня — день народження мами
       • 3 червня — прийом до лікаря"
```

### Deleting a reminder

```
User: "Видали нагадування про прийом до лікаря"
Bot:  "Видалено нагадування: прийом до лікаря."
```

### Morning standup (Mon–Fri, configurable time, default 09:00)

```
Bot:  "Доброго ранку! 📋 Незавершене з учорашнього дня:
       - зафіксити баг входу
       - переглянути PR #42

       Що плануєш на сьогодні? (відповідай списком, кожне завдання з нового рядка)"

User: "дописати документацію API
       подзвонити постачальнику"

Bot:  "Збережено! 2 завдання на сьогодні. Вдачі!"
```

### Evening check-in (Mon–Fri, configurable time, default 18:00)

```
Bot:  "Кінець дня! Що вдалось зробити?
       1. дописати документацію API
       2. подзвонити постачальнику

       Надішли номери виконаних завдань (наприклад: '1 2')"

User: "1"

Bot:  "Чудово! 1 виконано, 1 переноситься на завтра."
```

### Reminder notification (automatic)

```
Bot:  "⏰ Нагадування: завтра — день народження мами (15 травня)"
```

---

## Scheduler Jobs

| Job                  | Schedule                  | Description                                              |
|----------------------|---------------------------|----------------------------------------------------------|
| `check_reminders`    | Daily at morning time     | Fires due 7-day, 1-day, and day-of reminders             |
| `morning_standup`    | Mon–Fri at MORNING_TIME   | Sends pending tasks from yesterday + asks for today's    |
| `evening_checkin`    | Mon–Fri at EVENING_TIME   | Asks which tasks were completed                          |

---

## Configuration (`.env`)

```env
BOT_TOKEN=your_telegram_bot_token
CHAT_ID=your_telegram_chat_id
MORNING_TIME=09:00
EVENING_TIME=18:00
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_HOST=http://localhost:11434
WHISPER_MODEL=small
```

`config.py` validates all required fields at startup and raises a clear error if any are missing.

---

## Error Handling

- If Ollama is unreachable: bot replies "Не вдалось розпізнати повідомлення. Спробуй ще раз."
- If Whisper transcription fails: bot replies "Не вдалось розпізнати голосове повідомлення. Спробуй написати текстом."
- If intent is `unknown`: bot replies "Не зрозумів. Спробуй переформулювати."
- All unhandled exceptions are logged to `bot.log` and the bot continues running.

---

## Scalability Notes

- `chat_id` is stored on every row — multiple users can be added with zero schema changes
- SQLite is sufficient for personal/small-group use; migration to PostgreSQL is a connection-string change
- Warehouse product tracking can be added as a new table + new intents without touching existing code
- Swapping Ollama for Claude/Gemini API requires changing only `nlp.py`

---

## Out of Scope (this version)

- Warehouse product tracking (future)
- Web UI or dashboard
- Multi-user management / admin commands
- Recurring reminders (e.g. "every Monday")
