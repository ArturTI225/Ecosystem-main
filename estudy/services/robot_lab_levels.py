from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

LEVELS_ROOT = Path(__file__).resolve().parents[1] / "robot_lab" / "levels"
LEVELS_INDEX = LEVELS_ROOT / "index.json"


class RobotLabLevelNotFoundError(KeyError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid JSON object in {path}")
    return data


@lru_cache(maxsize=1)
def load_levels_index() -> dict[str, Any]:
    if not LEVELS_INDEX.exists():
        raise FileNotFoundError(f"Robot Lab levels index not found: {LEVELS_INDEX}")
    data = _read_json(LEVELS_INDEX)
    levels = data.get("levels")
    if not isinstance(levels, list):
        raise ValueError("Robot Lab levels index must contain a 'levels' list")
    return data


@lru_cache(maxsize=128)
def load_level(level_id: str) -> dict[str, Any]:
    level = get_level_entry(level_id)
    file_name = str(level.get("file") or "").strip()
    if not file_name:
        raise ValueError(f"Level {level_id} is missing file reference")
    path = LEVELS_ROOT / file_name
    if not path.exists():
        raise FileNotFoundError(f"Robot Lab level file not found: {path}")
    data = _read_json(path)
    data.setdefault("id", level_id)
    return data


def list_level_entries() -> list[dict[str, Any]]:
    index = load_levels_index()
    items = []
    for raw in index.get("levels", []):
        if not isinstance(raw, dict):
            continue
        if not raw.get("id"):
            continue
        items.append(dict(raw))
    items.sort(key=lambda x: (int(x.get("world", 0)), int(x.get("order", 0))))
    return items


def ordered_level_ids() -> list[str]:
    return [str(item["id"]) for item in list_level_entries()]


def get_level_entry(level_id: str) -> dict[str, Any]:
    target = str(level_id or "").strip()
    for item in list_level_entries():
        if str(item.get("id")) == target:
            return item
    raise RobotLabLevelNotFoundError(target)


def next_level_id(level_id: str) -> str | None:
    level_ids = ordered_level_ids()
    try:
        idx = level_ids.index(str(level_id))
    except ValueError:
        return None
    nxt = idx + 1
    if nxt >= len(level_ids):
        return None
    return level_ids[nxt]


def level_map_size(level_spec: dict[str, Any]) -> list[int]:
    grid = level_spec.get("grid") or []
    if not isinstance(grid, list) or not grid:
        return [0, 0]
    width = len(str(grid[0]))
    return [len(grid), width]
