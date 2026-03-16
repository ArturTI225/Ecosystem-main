from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.models import User
from django.db import transaction

from ..models import EventLog, RobotLabRun
from .audit_logger import log_event
from .robot_lab_levels import load_level
from .robot_lab_mentor import build_robo_mentor_response
from .robot_lab_progress import (
    apply_robot_lab_run_progress,
    build_robot_lab_progress_summary,
    ensure_robot_lab_progress_rows,
)
from .robot_lab_runner_client import execute_robot_lab_code

ERROR_TYPES = {"runtime", "logic", "timeout", "syntax", "none"}


class RobotLabRunBlockedError(ValueError):
    pass


def _normalize_error_type(value: Any) -> str:
    text = str(value or "logic").strip().lower()
    return text if text in ERROR_TYPES else "logic"


def _extract_primary_error(result: dict[str, Any]) -> str:
    explicit = str(result.get("primary_error") or "").strip()
    if explicit:
        return explicit
    trace = result.get("execution_trace") or []
    if isinstance(trace, list):
        for item in reversed(trace):
            if not isinstance(item, dict):
                continue
            err = str(item.get("error") or "").strip()
            if err:
                return err
    return ""


@transaction.atomic
def run_robot_lab_attempt(
    *,
    user: User,
    level_id: str,
    student_code: str,
    student_requested_solution: bool = False,
    hints_used: int = 0,
) -> dict[str, Any]:
    level = load_level(level_id)
    progress_map = ensure_robot_lab_progress_rows(user)
    level_progress = progress_map.get(level_id)
    if not level_progress or not level_progress.unlocked:
        raise RobotLabRunBlockedError("Level is locked for this user")

    attempt_number = int(level_progress.attempts_count or 0) + 1
    run_id = str(uuid.uuid4())
    allowed_api = list(level.get("allowed_api") or [])
    max_steps = int(level.get("max_steps") or 200)
    time_limit_ms = int(level.get("time_limit_ms") or 800)

    runner_result = execute_robot_lab_code(
        level_id=level_id,
        student_code=student_code,
        level_spec=level,
        allowed_api=allowed_api,
        max_steps=max_steps,
        time_limit_ms=time_limit_ms,
        run_id=run_id,
    )

    error_type = _normalize_error_type(runner_result.get("error_type"))
    primary_error = _extract_primary_error(runner_result)
    trace = (
        runner_result.get("execution_trace")
        if isinstance(runner_result.get("execution_trace"), list)
        else []
    )
    final_state = (
        runner_result.get("final_state")
        if isinstance(runner_result.get("final_state"), dict)
        else {}
    )
    steps_used = int(runner_result.get("steps_used") or 0)
    duration_ms = int(runner_result.get("duration_ms") or 0)
    solved = error_type == "none"

    mentor_payload = {
        "level_id": level_id,
        "goal": level.get("goal_text")
        or level.get("goal", {}).get("type", "Reach the goal"),
        "concepts": level.get("concepts") or [],
        "student_code": student_code,
        "execution_trace": trace,
        "error_type": error_type,
        "primary_error": primary_error,
        "attempt_number": attempt_number,
        "student_requested_solution": bool(student_requested_solution),
        "hints_used": max(0, int(hints_used or 0)),
        "history": list(
            user.robot_lab_attempt_logs.order_by("-id").values(
                "attempt_number", "error_type", "primary_error"
            )[:5]
        ),
        "level_metadata": {
            "max_steps": max_steps,
            "allowed_api": allowed_api,
            "map_size": level.get("map_size")
            or [len(level.get("grid") or []), len((level.get("grid") or [""])[0])],
            "difficulty": level.get("difficulty") or "easy",
        },
    }
    mentor_response = build_robo_mentor_response(mentor_payload, user=user)

    run = RobotLabRun.objects.create(
        user=user,
        level_id=level_id,
        attempt_number=attempt_number,
        code=student_code,
        error_type=error_type,
        primary_error=primary_error,
        execution_trace=trace,
        final_state=final_state,
        level_snapshot=level,
        steps_used=max(0, steps_used),
        duration_ms=max(0, duration_ms),
        solved=solved,
    )

    progress_result = apply_robot_lab_run_progress(
        user=user,
        level_id=level_id,
        solved=solved,
        steps_used=max(0, steps_used),
        xp_reward=int(level.get("xp_reward") or 0),
    )

    xp_granted = int(progress_result.get("xp_granted") or 0)
    if xp_granted > 0:
        profile = getattr(user, "userprofile", None)
        if profile is not None:
            profile.add_xp(xp_granted, reason=f"Robot Lab {level_id}")

    log_event(
        EventLog.EVENT_TEST_SUBMIT,
        user=user,
        metadata={
            "robot_lab": True,
            "run_id": run.id,
            "level_id": level_id,
            "attempt_number": attempt_number,
            "error_type": error_type,
            "primary_error": primary_error,
            "solved": solved,
            "steps_used": max(0, steps_used),
            "duration_ms": max(0, duration_ms),
            "xp_granted": xp_granted,
        },
    )

    return {
        "run_id": run.id,
        "level_id": level_id,
        "attempt_number": attempt_number,
        "error_type": error_type,
        "primary_error": primary_error,
        "execution_trace": trace,
        "final_state": final_state,
        "steps_used": max(0, steps_used),
        "duration_ms": max(0, duration_ms),
        "solved": solved,
        "mentor": mentor_response,
        "progress": progress_result.get("summary")
        or build_robot_lab_progress_summary(user),
        "level_progress": progress_result.get("level_progress") or {},
        "xp_granted": xp_granted,
    }
