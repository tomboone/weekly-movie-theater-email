import json
from pathlib import Path


def load_state(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"last_run": None, "movies": []}
    with open(p) as f:
        return json.load(f)


def save_state(path: str, date: str, movies: list[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump({"last_run": date, "movies": sorted(movies)}, f, indent=2)


def diff_movies(previous: list[str], current: list[str]) -> list[str]:
    previous_set = set(previous)
    return [m for m in current if m not in previous_set]
