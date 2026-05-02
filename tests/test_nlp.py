# tests/test_nlp.py
import json
import pytest
from unittest.mock import MagicMock, patch


def _make_response(payload: dict) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = {"result": {"response": json.dumps(payload)}, "success": True}
    mock.raise_for_status = MagicMock()
    return mock


@patch("nlp.httpx.post")
def test_parse_add_reminder(mock_post):
    mock_post.return_value = _make_response({
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


@patch("nlp.httpx.post")
def test_parse_add_tasks(mock_post):
    mock_post.return_value = _make_response({
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


@patch("nlp.httpx.post")
def test_parse_complete_tasks(mock_post):
    mock_post.return_value = _make_response({
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


@patch("nlp.httpx.post")
def test_cf_request_error_raises_runtime_error(mock_post):
    import httpx
    mock_post.side_effect = httpx.RequestError("connection refused")
    from nlp import parse_message
    with pytest.raises(RuntimeError, match="CF error"):
        parse_message("test", "2026-05-01")


@patch("nlp.httpx.post")
def test_invalid_json_response_raises_runtime_error(mock_post):
    mock = MagicMock()
    mock.json.return_value = {"result": {"response": "not json {"}, "success": True}
    mock.raise_for_status = MagicMock()
    mock_post.return_value = mock
    from nlp import parse_message
    with pytest.raises(RuntimeError, match="CF error"):
        parse_message("test", "2026-05-01")
