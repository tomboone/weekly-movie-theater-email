import json

from state import diff_movies, load_state, save_state


def test_load_state_missing_file(tmp_path):
    path = str(tmp_path / "nonexistent.json")
    state = load_state(path)
    assert state == {"last_run": None, "movies": []}


def test_load_state_existing_file(tmp_path):
    path = str(tmp_path / "state.json")
    data = {"last_run": "2026-03-13", "movies": ["Movie A", "Movie B"]}
    with open(path, "w") as f:
        json.dump(data, f)

    state = load_state(path)
    assert state["last_run"] == "2026-03-13"
    assert state["movies"] == ["Movie A", "Movie B"]


def test_save_state(tmp_path):
    path = str(tmp_path / "state.json")
    save_state(path, "2026-03-20", ["Movie A", "Movie C"])

    with open(path) as f:
        data = json.load(f)
    assert data["last_run"] == "2026-03-20"
    assert data["movies"] == ["Movie A", "Movie C"]


def test_save_state_creates_parent_dirs(tmp_path):
    path = str(tmp_path / "nested" / "dir" / "state.json")
    save_state(path, "2026-03-20", ["Movie A"])

    with open(path) as f:
        data = json.load(f)
    assert data["movies"] == ["Movie A"]


def test_diff_movies_finds_new():
    previous = ["Movie A", "Movie B"]
    current = ["Movie A", "Movie B", "Movie C", "Movie D"]
    new = diff_movies(previous, current)
    assert set(new) == {"Movie C", "Movie D"}


def test_diff_movies_first_run():
    previous = []
    current = ["Movie A", "Movie B"]
    new = diff_movies(previous, current)
    assert set(new) == {"Movie A", "Movie B"}


def test_diff_movies_no_new():
    previous = ["Movie A", "Movie B"]
    current = ["Movie A", "Movie B"]
    new = diff_movies(previous, current)
    assert new == []
