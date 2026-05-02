import json
import httpx
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
- list_tasks: user asks what tasks they have today
- unknown: anything else

Today is {today}. Resolve relative dates like "tomorrow" or "наступного понеділка" to ISO format."""


def parse_message(text: str, today: str) -> dict:
    """Call Cloudflare Workers AI and return parsed intent dict. Raises RuntimeError on any failure."""
    url = (
        f"https://api.cloudflare.com/client/v4/accounts"
        f"/{config.cf_account_id}/ai/run/{config.cf_model}"
    )
    payload = {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT.format(today=today)},
            {"role": "user", "content": text},
        ],
    }
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {config.cf_api_token}"},
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["result"]["response"]
        return json.loads(content)
    except (httpx.RequestError, httpx.HTTPStatusError, json.JSONDecodeError, KeyError) as exc:
        raise RuntimeError(f"CF error: {exc}") from exc
