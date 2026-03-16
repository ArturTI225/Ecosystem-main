from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any

SAFE_BUILTINS = {
    "range": range,
    "len": len,
    "min": min,
    "max": max,
    "abs": abs,
    "int": int,
    "float": float,
    "bool": bool,
}

FORBIDDEN_NODES = (
    ast.Import,
    ast.ImportFrom,
    ast.With,
    ast.Try,
    ast.Raise,
    ast.Lambda,
    ast.ClassDef,
    ast.Global,
    ast.Nonlocal,
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
)


class RobotRuntimeError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class StepLimitExceeded(RobotRuntimeError):
    def __init__(self):
        super().__init__("step_limit_exceeded")


@dataclass
class RobotState:
    row: int
    col: int
    direction: str = "E"


class RobotWorld:
    DIRECTIONS = ["N", "E", "S", "W"]
    DELTAS = {
        "N": (-1, 0),
        "E": (0, 1),
        "S": (1, 0),
        "W": (0, -1),
    }
    ITEM_BY_TILE = {"B": "battery", "K": "key"}

    def __init__(self, *, level_spec: dict[str, Any], max_steps: int):
        self.level_spec = level_spec
        self.grid = [list(str(row)) for row in (level_spec.get("grid") or [])]
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows else 0
        self.max_steps = max(1, int(max_steps))
        self.state = self._find_start()
        self.goal_positions = self._find_tiles("G")
        self.terminal_positions = self._find_tiles("T")
        self.trace: list[dict[str, Any]] = []
        self.steps = 0
        self.inventory: set[str] = set()
        self.terminal_activated = False

    def _find_tiles(self, tile: str) -> set[tuple[int, int]]:
        found = set()
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == tile:
                    found.add((r, c))
        return found

    def _find_start(self) -> RobotState:
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == "S":
                    return RobotState(
                        row=r,
                        col=c,
                        direction=str(self.level_spec.get("start_dir") or "E").upper(),
                    )
        return RobotState(row=0, col=0, direction="E")

    def _tile(self, r: int, c: int) -> str:
        if r < 0 or c < 0 or r >= self.rows or c >= self.cols:
            return "#"
        return self.grid[r][c]

    def _front(self) -> tuple[int, int]:
        dr, dc = self.DELTAS[self.state.direction]
        return self.state.row + dr, self.state.col + dc

    def _is_walkable(self, tile: str) -> bool:
        if tile == "#":
            return False
        if tile == "D":
            return "key" in self.inventory
        return True

    def _add_trace(self, action: str, *, error: str = "") -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceeded()
        item: dict[str, Any] = {
            "step": self.steps,
            "action": action,
            "position": [self.state.row, self.state.col],
            "dir": self.state.direction,
        }
        if error:
            item["error"] = error
        self.trace.append(item)

    # API actions
    def move(self) -> None:
        nr, nc = self._front()
        tile = self._tile(nr, nc)
        if not self._is_walkable(tile):
            self._add_trace("move", error="hit_wall")
            raise RobotRuntimeError("hit_wall")
        self.state.row, self.state.col = nr, nc
        self._add_trace("move")
        if tile == "H":
            self.trace[-1]["error"] = "stepped_on_hazard"
            raise RobotRuntimeError("stepped_on_hazard")

    def turn_left(self) -> None:
        idx = self.DIRECTIONS.index(self.state.direction)
        self.state.direction = self.DIRECTIONS[(idx - 1) % 4]
        self._add_trace("turn_left")

    def turn_right(self) -> None:
        idx = self.DIRECTIONS.index(self.state.direction)
        self.state.direction = self.DIRECTIONS[(idx + 1) % 4]
        self._add_trace("turn_right")

    def pick(self) -> None:
        tile = self._tile(self.state.row, self.state.col)
        name = self.ITEM_BY_TILE.get(tile)
        if not name:
            self._add_trace("pick", error="no_item_to_pick")
            raise RobotRuntimeError("no_item_to_pick")
        self.inventory.add(name)
        self.grid[self.state.row][self.state.col] = "."
        self._add_trace("pick")

    def activate(self) -> None:
        if not self.near_terminal():
            self._add_trace("activate", error="cannot_activate")
            raise RobotRuntimeError("cannot_activate")
        self.terminal_activated = True
        self._add_trace("activate")

    # sensors
    def front_is_clear(self) -> bool:
        nr, nc = self._front()
        return self._is_walkable(self._tile(nr, nc))

    def at_goal(self) -> bool:
        return (self.state.row, self.state.col) in self.goal_positions

    def on_item(self) -> bool:
        tile = self._tile(self.state.row, self.state.col)
        return tile in self.ITEM_BY_TILE

    def near_terminal(self) -> bool:
        for tr, tc in self.terminal_positions:
            if abs(tr - self.state.row) + abs(tc - self.state.col) <= 1:
                return True
        return False

    def has_item(self, name: str) -> bool:
        return str(name) in self.inventory

    def final_state(self) -> dict[str, Any]:
        return {
            "position": [self.state.row, self.state.col],
            "direction": self.state.direction,
            "inventory": sorted(self.inventory),
            "terminal_activated": self.terminal_activated,
            "at_goal": self.at_goal(),
        }

    def goal_result(self) -> tuple[bool, str]:
        goal = self.level_spec.get("goal") or {}
        goal_type = str(goal.get("type") or "reach_goal")
        if goal_type == "reach_goal":
            if self.at_goal():
                return True, ""
            return False, "not_reached_goal"
        if goal_type == "activate_terminal":
            if self.terminal_activated:
                return True, ""
            return False, "missing_activate"
        if goal_type == "deliver_item":
            item = str(goal.get("item") or "").strip().lower()
            if item and item not in self.inventory:
                return False, "missing_pick"
            if not self.at_goal():
                return False, "wrong_delivery"
            return True, ""
        return (self.at_goal(), "" if self.at_goal() else "not_reached_goal")


def validate_code_ast(code: str, allowed_api: set[str]) -> None:
    if len(code or "") > 10000:
        raise SyntaxError("code_too_long")
    tree = ast.parse(code or "")

    for node in ast.walk(tree):
        if isinstance(node, FORBIDDEN_NODES):
            raise SyntaxError(f"forbidden_syntax:{type(node).__name__}")
        if isinstance(node, ast.Attribute):
            raise SyntaxError("forbidden_attribute_access")
        if isinstance(node, ast.Name) and str(node.id).startswith("__"):
            raise SyntaxError("forbidden_identifier")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise SyntaxError("forbidden_call_shape")
            fn = str(node.func.id)
            if fn not in allowed_api and fn not in SAFE_BUILTINS:
                raise SyntaxError(f"forbidden_call:{fn}")


def run_student_code(
    *,
    level_id: str,
    student_code: str,
    level_spec: dict[str, Any],
    allowed_api: list[str],
    max_steps: int,
) -> dict[str, Any]:
    allowed = set(allowed_api or [])

    try:
        validate_code_ast(student_code, allowed)
    except SyntaxError as exc:
        return {
            "status": "error",
            "error_type": "syntax",
            "primary_error": str(exc),
            "execution_trace": [],
            "final_state": {},
            "steps_used": 0,
        }

    world = RobotWorld(level_spec=level_spec, max_steps=max_steps)
    globals_scope = {
        "__builtins__": SAFE_BUILTINS,
        "move": world.move,
        "turn_left": world.turn_left,
        "turn_right": world.turn_right,
        "pick": world.pick,
        "activate": world.activate,
        "front_is_clear": world.front_is_clear,
        "at_goal": world.at_goal,
        "on_item": world.on_item,
        "near_terminal": world.near_terminal,
        "has_item": world.has_item,
    }

    try:
        compiled = compile(student_code, f"<robot-lab:{level_id}>", "exec")
        exec(compiled, globals_scope, {})
    except StepLimitExceeded as exc:
        return {
            "status": "error",
            "error_type": "timeout",
            "primary_error": exc.code,
            "execution_trace": world.trace,
            "final_state": world.final_state(),
            "steps_used": world.steps,
        }
    except RobotRuntimeError as exc:
        return {
            "status": "error",
            "error_type": "runtime",
            "primary_error": exc.code,
            "execution_trace": world.trace,
            "final_state": world.final_state(),
            "steps_used": world.steps,
        }
    except SyntaxError as exc:
        return {
            "status": "error",
            "error_type": "syntax",
            "primary_error": str(exc),
            "execution_trace": world.trace,
            "final_state": world.final_state(),
            "steps_used": world.steps,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "error",
            "error_type": "runtime",
            "primary_error": f"invalid_action:{exc.__class__.__name__}",
            "execution_trace": world.trace,
            "final_state": world.final_state(),
            "steps_used": world.steps,
        }

    solved, primary = world.goal_result()
    if solved:
        return {
            "status": "ok",
            "error_type": "none",
            "primary_error": "",
            "execution_trace": world.trace,
            "final_state": world.final_state(),
            "steps_used": world.steps,
        }
    return {
        "status": "error",
        "error_type": "logic",
        "primary_error": primary or "not_reached_goal",
        "execution_trace": world.trace,
        "final_state": world.final_state(),
        "steps_used": world.steps,
    }
