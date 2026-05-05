import os
import pytest

# Must be set before any module importing config is loaded.
os.environ.setdefault("BOT_TOKEN", "test_token")
os.environ.setdefault("CHAT_ID", "12345")
os.environ.setdefault("MORNING_TIME", "09:00")
os.environ.setdefault("EVENING_TIME", "18:00")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("WHISPER_MODEL", "small")


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    import db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    yield


@pytest.fixture(autouse=True)
def reset_state(isolated_db):
    import state
    state.clear_all()
    yield
    state.clear_all()
