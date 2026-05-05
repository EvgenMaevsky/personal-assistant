# tests/test_config.py
import os
import pytest


def test_config_reads_env_vars():
    from config import Config
    cfg = Config()
    assert cfg.bot_token == "test_token"
    assert cfg.chat_id == 12345
    assert cfg.morning_time == "09:00"
    assert cfg.evening_time == "18:00"
    assert cfg.anthropic_api_key == "sk-ant-test"
    assert cfg.whisper_model == "small"


def test_invalid_morning_time_raises(monkeypatch):
    monkeypatch.setenv("MORNING_TIME", "25:00")
    from config import Config
    with pytest.raises(Exception):
        Config()


def test_invalid_evening_time_raises(monkeypatch):
    monkeypatch.setenv("EVENING_TIME", "18:99")
    from config import Config
    with pytest.raises(Exception):
        Config()


def test_non_numeric_time_raises(monkeypatch):
    monkeypatch.setenv("MORNING_TIME", "9:00")
    from config import Config
    with pytest.raises(Exception):
        Config()
