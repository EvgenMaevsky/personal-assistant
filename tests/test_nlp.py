# tests/test_nlp.py
import json
import pytest
from unittest.mock import MagicMock, patch


def _make_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    block = MagicMock()
    block.text = json.dumps(payload)
    mock.content = [block]
    return mock


@patch("nlp._client")
def test_parse_add_reminder(mock_client):
    mock_client.messages.create.return_value = _make_response({
        "intent": "add_reminder",
        "title": "день народження мами",
        "date": "2026-05-15",
        "tasks": [],
        "task_indices": [],
    })
    from nlp import parse_message
    result = parse_message("Нагадай про день народження мами 15 травня", "2026-05-01")
    assert result["intent"] == "add_reminder"
    assert result["title"] == "день народження мами"
    assert result["date"] == "2026-05-15"


@patch("nlp._client")
def test_parse_add_tasks(mock_client):
    mock_client.messages.create.return_value = _make_response({
        "intent": "add_tasks",
        "title": "",
        "date": "",
        "tasks": ["фіксити баг", "дзвонити клієнту"],
        "task_indices": [],
    })
    from nlp import parse_message
    result = parse_message("Сьогодні буду: фіксити баг, дзвонити клієнту", "2026-05-01")
    assert result["intent"] == "add_tasks"
    assert "фіксити баг" in result["tasks"]


@patch("nlp._client")
def test_parse_complete_tasks(mock_client):
    mock_client.messages.create.return_value = _make_response({
        "intent": "complete_tasks",
        "title": "",
        "date": "",
        "tasks": [],
        "task_indices": [1, 2],
    })
    from nlp import parse_message
    result = parse_message("Зробив перше і друге", "2026-05-01")
    assert result["intent"] == "complete_tasks"
    assert result["task_indices"] == [1, 2]


@patch("nlp._client")
def test_api_error_raises_runtime_error(mock_client):
    import anthropic
    mock_client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())
    from nlp import parse_message
    with pytest.raises(RuntimeError, match="Claude API error"):
        parse_message("test", "2026-05-01")


@patch("nlp._client")
def test_invalid_json_response_raises_runtime_error(mock_client):
    mock = MagicMock()
    block = MagicMock()
    block.text = "not json {"
    mock.content = [block]
    mock_client.messages.create.return_value = mock
    from nlp import parse_message
    with pytest.raises(RuntimeError, match="Claude API error"):
        parse_message("test", "2026-05-01")
