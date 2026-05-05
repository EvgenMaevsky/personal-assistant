import json
import anthropic
from config import config

_SYSTEM_PROMPT = """You are a JSON extraction assistant for a personal assistant bot.
The user speaks Ukrainian or English. Extract the intent and entities from their message.

Return ONLY valid JSON in exactly this format:
{{
  "intent": "<intent>",
  "title": "<event or task title, or empty string>",
  "date": "<ISO date YYYY-MM-DD, or empty string>",
  "tasks": ["<task 1>", "<task 2>"],
  "task_indices": [1, 2]
}}

Valid intents:
- add_reminder: user wants to remember a date-based event (put event name in title, date in date)
- list_reminders: user asks to see their reminders
- delete_reminder: user wants to remove a reminder (put event name in title)
- add_tasks: user lists work tasks (put them in tasks array)
- complete_tasks: user says which tasks they finished (put 1-based numbers in task_indices)
- start_tasks: user says they are starting/working on a task (put 1-based numbers in task_indices)
- cancel_tasks: user wants to cancel/skip/drop a task (put 1-based numbers in task_indices)
- list_tasks: user asks what tasks they have today
- unknown: anything else

Today is {today}. Resolve relative dates like "tomorrow" or "наступного понеділка" to ISO format."""

_client = anthropic.Anthropic(api_key=config.anthropic_api_key)


def parse_message(text: str, today: str) -> dict:
    """Call Claude API and return parsed intent dict. Raises RuntimeError on any failure."""
    try:
        response = _client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system=_SYSTEM_PROMPT.format(today=today),
            messages=[{"role": "user", "content": text}],
        )
        return json.loads(response.content[0].text)
    except (anthropic.APIError, json.JSONDecodeError, IndexError) as exc:
        raise RuntimeError(f"Claude API error: {exc}") from exc
