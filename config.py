import re

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    bot_token: str
    chat_id: int
    morning_time: str = "09:00"
    evening_time: str = "18:00"
    ollama_model: str = "qwen2.5:3b"
    ollama_host: str = "http://localhost:11434"
    whisper_model: str = "small"

    @field_validator("morning_time", "evening_time")
    @classmethod
    def valid_time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError(f"Time must be HH:MM (e.g. 09:00), got: {v}")
        h, m = int(v[:2]), int(v[3:5])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"Time out of range: {v}")
        return v

    model_config = {"env_file": ".env"}


config = Config()
