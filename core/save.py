"""Remembers your pets between runs in state.json (see core/paths.py for where)."""

import json

from core.paths import config_dir

CONFIG_DIR = config_dir()
STATE_FILE = CONFIG_DIR / "state.json"


def load() -> dict | None:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and isinstance(data.get("pets"), list) else None


def save(data: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_FILE)  # atomic: a crash mid-write never corrupts the save
