from __future__ import annotations

import random
import re
from typing import Any, Dict, List

from django.conf import settings

from ..models import Lesson, LessonMedia, LessonProgress
from ..views import _is_competitor_link
from .gamification import get_badge_summary
from .lesson_access import compute_accessibility
from .recommendations import refresh_recommendations

INTRO_LESSON_COUNT = 2
CYRILLIC_RE = re.compile(r"[А-Яа-яЁёІіЇїЄєҐґ]")


def _contains_cyrillic(value: str) -> bool:
    return bool(CYRILLIC_RE.search(value or ""))


def _sanitize_display_text(value: str | None, fallback: str = "") -> str:
    text = (value or "").strip()
    if not text or _contains_cyrillic(text):
        return fallback
    return text


def _sanitize_display_list(
    values: list[str] | tuple[str, ...] | None, fallback: list[str] | None = None
) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        candidate = _sanitize_display_text(str(value), "")
        if candidate:
            cleaned.append(candidate)
    if cleaned:
        return cleaned
    return list(fallback or [])


class BlockingLessonRequired(Exception):
    def __init__(self, blocking_slug: str, blocking_title: str | None = None):
        super().__init__(f"Blocking lesson required: {blocking_slug}")
        self.blocking_slug = blocking_slug
        self.blocking_title = blocking_title


def _get_lesson_enrichment(slug: str) -> dict[str, Any]:
    mapping = getattr(settings, "ESTUDY_LESSON_ENRICHMENTS", {})
    if not isinstance(mapping, dict):
        return {}
    enrichment = mapping.get(slug, {})
    return enrichment if isinstance(enrichment, dict) else {}


def _build_mentor_characters(lesson: Lesson) -> list[dict[str, str]]:
    hero_emoji = (lesson.hero_emoji or "").strip() or "🚀"
    return [
        {
            "name": "Nova",
            "emoji": hero_emoji,
            "role": "Căpitanul aventurii",
            "line": "Transformăm curiozitatea în pași mici și distractivi.",
        },
        {
            "name": "Byte",
            "emoji": "🤖",
            "role": "Mecanicul de cod",
            "line": "Îți arăt cum fiecare linie de cod face ceva concret.",
        },
        {
            "name": "Pixel",
            "emoji": "🦊",
            "role": "Exploratorul logicii",
            "line": "Dacă greșim, învățăm rapid și încercăm din nou.",
        },
    ]


def _build_code_arena_steps(
    code_exercises, enrichment: dict[str, Any]
) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    for idx, exercise in enumerate(code_exercises[:4], start=1):
        steps.append(
            {
                "title": exercise.title or f"Misiunea {idx}",
                "goal": (
                    exercise.description
                    or "Rezolvă provocarea scriind cod Python corect și clar."
                ),
                "xp": str(max(5, int(getattr(exercise, "points", 10) or 10))),
                "badge": f"Dificultate {getattr(exercise, 'difficulty_level', 1)}",
                "target": "#code-exercises",
            }
        )

    if not steps:
        challenges = enrichment.get("code_challenges") or []
        if isinstance(challenges, list):
            for idx, challenge in enumerate(challenges[:4], start=1):
                if not isinstance(challenge, dict):
                    continue
                steps.append(
                    {
                        "title": challenge.get("title") or f"Misiunea {idx}",
                        "goal": challenge.get("prompt")
                        or "Scrie un mic fragment de cod și verifică rezultatul.",
                        "xp": str(challenge.get("xp") or 10),
                        "badge": challenge.get("badge") or "Arena",
                        "target": "#example",
                    }
                )

    if steps:
        return steps

    return [
        {
            "title": "Misiunea 1: Încălzirea",
            "goal": "Declară variabile simple și afișează-le cu print().",
            "xp": "10",
            "badge": "Syntax",
            "target": "#example",
        },
        {
            "title": "Misiunea 2: Combo de logică",
            "goal": "Combină text și numere într-un mesaj clar pentru utilizator.",
            "xp": "15",
            "badge": "Flow",
            "target": "#practice",
        },
        {
            "title": "Misiunea 3: Boss mini-test",
            "goal": "Treci testul final și explică de ce soluția ta funcționează.",
            "xp": "20",
            "badge": "Mastery",
            "target": "#test",
        },
    ]


def prepare_lesson_detail(user, slug: str) -> dict:
    """Fetch a lesson and prepare the full payload for the view.

    Raises BlockingLessonRequired if a previous required lesson is not completed.
    Returns the payload dict (already containing 'lesson' and 'badges').
    """
    lesson = (
        Lesson.objects.select_related("subject")
        .prefetch_related(
            "materials",
            "tests",
            "code_exercises",
            "objectives",
            "reflection_prompts",
            "skills",
            "media__segments",
        )
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

    progress = LessonProgress.objects.filter(user=user, lesson=lesson).first()

    try:
        _, accessible_ids, locked_reasons = compute_accessibility(user)
    except Exception:
        accessible_ids = {lesson.id}
        locked_reasons = {}

    subject_completed_ids = set(
        LessonProgress.objects.filter(
            user=user, lesson__in=subject_lessons, completed=True
        ).values_list("lesson_id", flat=True)
    )

    payload = build_lesson_detail_payload(
        lesson,
        subject_lessons,
        current_index,
        subject_completed_ids,
        accessible_ids,
        locked_reasons,
        progress,
    )
    payload["lesson"] = lesson
    payload["badges"] = get_badge_summary(user)
    payload["recommendations"] = recs
    return payload


def build_lesson_detail_payload(
    lesson: Lesson,
    subject_lessons: List[Lesson],
    current_index: int,
    completed_in_subject: set,
    accessible_ids: set,
    locked_reasons: dict,
    progress: LessonProgress | None,
) -> Dict:
    """Build contextual payload for lesson_detail view.

    Returns keys used by template: tests, quiz_test, quiz_options, recommendations, enrichment,
    badges, practice, prev_lesson, next_lesson, next_locked, subject_sequence, lesson_position,
    subject_total, lesson_voice_text, lesson_materials
    """
    tests = list(lesson.tests.order_by("id"))
    quiz_test = tests[0] if tests else None
    quiz_options = []
    if quiz_test:
        quiz_options = [quiz_test.correct_answer, *quiz_test.wrong_answers]
        random.shuffle(quiz_options)

    # recommendations fetched in view/service caller (keep here optional)
    recommendations = []

    enrichment = _get_lesson_enrichment(lesson.slug)

    practice = getattr(lesson, "practice", None)
    code_exercises = list(lesson.code_exercises.order_by("order", "id"))
    is_intro_lesson = (current_index + 1) <= INTRO_LESSON_COUNT
    mentor_characters = _build_mentor_characters(lesson)
    code_arena_steps = _build_code_arena_steps(code_exercises, enrichment)
    lesson_intro_text = _sanitize_display_text(lesson.theory_intro, "")
    if not lesson_intro_text:
        lesson_intro_text = _sanitize_display_text(lesson.excerpt, "")
    if not lesson_intro_text:
        lesson_intro_text = "Descoperă cum poți folosi variabilele pentru a face programele mai inteligente."
    lesson_story_anchor = _sanitize_display_text(lesson.story_anchor, "")
    lesson_skill_titles = _sanitize_display_list(
        [skill.title for skill in lesson.skills.all()],
        ["Rezolvare de probleme", "Siguranță digitală"],
    )
    lesson_track_items = _sanitize_display_list(
        [str(track) for track in lesson.content_tracks],
        ["Traseu de bază", "Bonus pentru exploratori"],
    )
    lesson_theory_points = _sanitize_display_list(
        [str(point) for point in lesson.theory_points()],
        [],
    )
    lesson_content_text = _sanitize_display_text(
        lesson.content,
        "O variabilă păstrează o informație importantă pe care codul tău o poate folosi și modifica.",
    )

    prev_lesson = subject_lessons[current_index - 1] if current_index > 0 else None
    next_lesson = (
        subject_lessons[current_index + 1]
        if current_index < len(subject_lessons) - 1
        else None
    )
    next_locked = bool(next_lesson and next_lesson.id not in accessible_ids)

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
    if lesson_intro_text:
        info_snippets.append(lesson_intro_text)
    if lesson_theory_points:
        info_snippets.append("Puncte-cheie: " + "; ".join(lesson_theory_points))
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

    try:
        lesson_media = lesson.media
    except LessonMedia.DoesNotExist:
        lesson_media = None
    media_segments = []
    if lesson_media:
        media_segments = list(lesson_media.segments.order_by("order", "id"))

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
        "code_exercises": code_exercises,
        "lesson_media": lesson_media,
        "media_segments": media_segments,
        "is_intro_lesson": is_intro_lesson,
        "mentor_characters": mentor_characters,
        "code_arena_steps": code_arena_steps,
        "lesson_intro_text": lesson_intro_text,
        "lesson_story_anchor": lesson_story_anchor,
        "lesson_skill_titles": lesson_skill_titles,
        "lesson_track_items": lesson_track_items,
        "lesson_theory_points": lesson_theory_points,
        "lesson_content_text": lesson_content_text,
    }
