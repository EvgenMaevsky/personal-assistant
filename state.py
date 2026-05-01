_state: dict[int, str] = {}


def set_action(chat_id: int, action: str) -> None:
    _state[chat_id] = action


def get_action(chat_id: int) -> str | None:
    return _state.get(chat_id)


def clear_action(chat_id: int) -> None:
    _state.pop(chat_id, None)


def clear_all() -> None:
    _state.clear()
