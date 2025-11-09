from __future__ import annotations

import random
from typing import Dict, List

from ..models import Lesson, LessonProgress
from ..views import _is_competitor_link
from .gamification import get_badge_summary
from .recommendations import refresh_recommendations


class BlockingLessonRequired(Exception):
    def __init__(self, blocking_slug: str, blocking_title: str | None = None):
        super().__init__(f"Blocking lesson required: {blocking_slug}")
        self.blocking_slug = blocking_slug
        self.blocking_title = blocking_title


def prepare_lesson_detail(user, slug: str) -> dict:
    """Fetch a lesson and prepare the full payload for the view.

    Raises BlockingLessonRequired if a previous required lesson is not completed.
    Returns the payload dict (already containing 'lesson' and 'badges').
    """
    lesson = (
        Lesson.objects.select_related("subject")
        .prefetch_related("materials", "tests")
        .filter(slug=slug)
        .first()
    )
    if not lesson:
        raise ValueError("Lesson not found")

    subject_lessons = list(lesson.subject.lessons.order_by("date", "id"))
    current_index = next(
        (index for index, item in enumerate(subject_lessons) if item.id == lesson.id), 0
    )
    required_lessons = subject_lessons[:current_index]
    completed_in_subject = set(
        LessonProgress.objects.filter(
            user=user, lesson__in=required_lessons, completed=True
        ).values_list("lesson_id", flat=True)
    )
    blocking_lesson = next(
        (item for item in required_lessons if item.id not in completed_in_subject), None
    )
    if blocking_lesson:
        raise BlockingLessonRequired(
            blocking_slug=blocking_lesson.slug, blocking_title=blocking_lesson.title
        )

    # refresh recommendations and compute accessibility
    try:
        recs = refresh_recommendations(user)
    except Exception:
        recs = []

    try:
        from ..views import _compute_accessibility

        # we only need locked_reasons here; detailed accessibility is handled in the payload builder
        _, _, locked_reasons = _compute_accessibility(user)
    except Exception:
        locked_reasons = {}

    subject_completed_ids = set(
        LessonProgress.objects.filter(
            user=user, lesson__in=subject_lessons, completed=True
        ).values_list("lesson_id", flat=True)
    )

    payload = build_lesson_detail_payload(
        user,
        lesson,
        subject_lessons,
        current_index,
        subject_completed_ids,
        locked_reasons,
    )
    payload["lesson"] = lesson
    payload["badges"] = get_badge_summary(user)
    payload["recommendations"] = recs
    return payload


def build_lesson_detail_payload(
    user,
    lesson: Lesson,
    subject_lessons: List[Lesson],
    current_index: int,
    completed_in_subject: set,
    locked_reasons: dict,
) -> Dict:
    """Build contextual payload for lesson_detail view.

    Returns keys used by template: tests, quiz_test, quiz_options, recommendations, enrichment,
    badges, practice, prev_lesson, next_lesson, next_locked, subject_sequence, lesson_position,
    subject_total, lesson_voice_text, lesson_materials
    """
    progress = None  # left to view if needed
    tests = list(lesson.tests.order_by("id"))
    quiz_test = tests[0] if tests else None
    quiz_options = []
    if quiz_test:
        quiz_options = [quiz_test.correct_answer, *quiz_test.wrong_answers]
        random.shuffle(quiz_options)

    # recommendations fetched in view/service caller (keep here optional)
    recommendations = []

    enrichment = {}
    try:
        from ..views import LESSON_ENRICHMENTS

        enrichment = LESSON_ENRICHMENTS.get(lesson.slug, {})
    except Exception:
        enrichment = {}

    practice = getattr(lesson, "practice", None)

    # accessibility & sequence
    try:
        from ..views import _compute_accessibility

        _, accessible_ids, _ = _compute_accessibility(user)
    except Exception:
        accessible_ids = set()

    prev_lesson = subject_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = (
        subject_lessons[current_index + 1]
        if current_index < len(subject_lessons) - 1
        else None
    )
    next_locked = bool(
        next_lesson and not (progress and getattr(progress, "completed", False))
    )

    subject_sequence = []
    for idx, seq_lesson in enumerate(subject_lessons, start=1):
        subject_sequence.append(
            {
                "lesson": seq_lesson,
                "index": idx,
                "completed": seq_lesson.id in completed_in_subject,
                "accessible": seq_lesson.id in accessible_ids,
                "is_current": seq_lesson.id == lesson.id,
                "locked_reason": locked_reasons.get(seq_lesson.id),
            }
        )

    info_snippets = []
    if lesson.theory_intro:
        info_snippets.append(lesson.theory_intro)
    elif lesson.excerpt:
        info_snippets.append(lesson.excerpt)
    if lesson.theory_points():
        info_snippets.append("Puncte-cheie: " + "; ".join(lesson.theory_points()))
    if enrichment.get("story_steps"):
        story_text = "; ".join(
            step.get("detail", "")
            for step in enrichment["story_steps"]
            if step.get("detail")
        )
        if story_text:
            info_snippets.append(story_text)
    lesson_voice_text = " ".join(part for part in info_snippets if part).strip()

    lesson_materials = [
        m for m in lesson.materials.all() if not _is_competitor_link(m.url)
    ]

    return {
        "progress": progress,
        "tests": tests,
        "quiz_test": quiz_test,
        "quiz_options": quiz_options,
        "recommendations": recommendations,
        "enrichment": enrichment,
        "badges": None,  # badges fetched by caller
        "practice": practice,
        "prev_lesson": prev_lesson,
        "next_lesson": next_lesson,
        "next_locked": next_locked,
        "subject_sequence": subject_sequence,
        "lesson_position": current_index + 1,
        "subject_total": len(subject_lessons),
        "lesson_voice_text": lesson_voice_text,
        "lesson_materials": lesson_materials,
    }
