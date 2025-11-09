from __future__ import annotations

from typing import Dict

from ..models import Test, TestAttempt
from ..services.gamification import record_lesson_completion


def process_test_attempt(user, test: Test, answer: str, time_taken_ms: int = 0) -> Dict:
    """Process a test attempt: record attempt, compute correctness, points, bonus and
    mark lesson complete when correct.

    Returns a dict compatible with the JSON response used by the view.
    """
    is_correct = answer == test.correct_answer
    bonus = bool(
        is_correct
        and time_taken_ms
        and (time_taken_ms / 1000) <= test.bonus_time_threshold
    )
    awarded_points = test.points if is_correct else 0

    attempt, _ = TestAttempt.objects.update_or_create(
        test=test,
        user=user,
        defaults={
            "selected_answer": answer,
            "is_correct": is_correct,
            "time_taken_ms": time_taken_ms,
            "awarded_points": awarded_points,
            "earned_bonus": bonus,
            "feedback": test.explanation if not is_correct else "Grozaav!",
        },
    )

    response: Dict = {
        "is_correct": is_correct,
        "correct_answer": test.correct_answer,
        "explanation": test.explanation,
        "awarded_points": attempt.awarded_points,
        "earned_bonus": bonus,
    }

    if is_correct:
        # mark lesson completed (convert ms to seconds for record_lesson_completion)
        seconds = time_taken_ms // 1000 if time_taken_ms else None
        progress_snapshot = record_lesson_completion(
            user, test.lesson, seconds_spent=seconds
        )
        response.update(
            {
                "lesson_completed": True,
                "progress_percent": progress_snapshot["percent"],
                "completed_count": progress_snapshot["completed"],
                "total_lessons": progress_snapshot["total"],
            }
        )
    else:
        response["lesson_completed"] = False

    return response
