import state


def test_set_and_get_action():
    state.set_action(123, "awaiting_tasks")
    assert state.get_action(123) == "awaiting_tasks"


def test_clear_action_removes_entry():
    state.set_action(123, "awaiting_tasks")
    state.clear_action(123)
    assert state.get_action(123) is None


def test_unknown_chat_returns_none():
    assert state.get_action(999999) is None


def test_overwrite_action():
    state.set_action(1, "awaiting_tasks")
    state.set_action(1, "awaiting_completion")
    assert state.get_action(1) == "awaiting_completion"


def test_clear_all_empties_dict():
    state.set_action(1, "awaiting_tasks")
    state.set_action(2, "awaiting_completion")
    state.clear_all()
    assert state.get_action(1) is None
    assert state.get_action(2) is None
