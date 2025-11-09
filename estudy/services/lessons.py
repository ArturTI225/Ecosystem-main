from __future__ import annotations

from typing import Dict, List, Set

from ..models import LearningPath, Lesson


def build_lesson_blocks(
    subjects: List,
    lessons: List[Lesson],
    completed_ids: Set[int],
    accessible_ids: Set[int],
    learning_paths: List[LearningPath],
):
    """Builds lesson blocks (paths + subject blocks) for lessons listing.

    Returns a list of blocks suitable for the templates.
    """
    sequence_lookup: Dict[int, Dict] = {}

    for subject in subjects:
        lesson_sequence = []
        for index, subj_lesson in enumerate(subject.lessons.all(), start=1):
            lesson_sequence.append(
                {
                    "lesson": subj_lesson,
                    "index": index,
                    "completed": subj_lesson.id in completed_ids,
                    "accessible": subj_lesson.id in accessible_ids,
                }
            )
        subject.completed_count = sum(
            1 for item in lesson_sequence if item["completed"]
        )
        subject.total_lessons = len(lesson_sequence)
        for item in lesson_sequence:
            item["total"] = subject.total_lessons
            sequence_lookup[item["lesson"].id] = item
        subject.lesson_sequence = lesson_sequence

    lesson_lookup = {lesson.id: lesson for lesson in lessons}
    assigned_lessons = set()
    path_blocks = []

    for path in learning_paths:
        block_lessons = []
        for item in path.items.all():
            lesson = lesson_lookup.get(item.lesson_id)
            if not lesson:
                continue
            setattr(lesson, "block_order", item.order)
            assigned_lessons.add(lesson.id)
            block_lessons.append(lesson)
        if not block_lessons:
            continue
        block_lessons.sort(key=lambda lesson: getattr(lesson, "block_order", 0))
        total_in_block = len(block_lessons)
        completed_in_block = sum(
            1 for lesson in block_lessons if getattr(lesson, "is_completed", False)
        )
        progress_percent = (
            int(round((completed_in_block / total_in_block) * 100))
            if total_in_block
            else 0
        )
        next_candidate = next(
            (
                lesson
                for lesson in block_lessons
                if getattr(lesson, "is_accessible", False)
                and not getattr(lesson, "is_completed", False)
            ),
            None,
        )
        if next_candidate is None:
            next_candidate = block_lessons[0]
        path_blocks.append(
            {
                "title": path.title,
                "slug": path.slug,
                "description": path.description,
                "theme": path.theme,
                "audience": getattr(path, "audience", "general"),
                "difficulty_label": (
                    path.get_difficulty_display()
                    if hasattr(path, "get_difficulty_display")
                    else path.difficulty
                ),
                "lessons": block_lessons,
                "completed": completed_in_block,
                "total": total_in_block,
                "progress_percent": progress_percent,
                "type": "path",
                "model": path,
                "next_lesson": next_candidate,
            }
        )

    leftover_by_subject = {}
    for lesson in lessons:
        if lesson.id in assigned_lessons:
            continue
        leftover_by_subject.setdefault(lesson.subject, []).append(lesson)

    subject_blocks = []
    for subject, subject_lessons in leftover_by_subject.items():
        subject_lessons.sort(
            key=lambda lesson: (
                (
                    (getattr(lesson, "sequence", {}) or {}).get("index")
                    if isinstance(getattr(lesson, "sequence", {}), dict)
                    else float("inf")
                ),
                lesson.date,
                lesson.id,
            )
        )
        total_in_block = len(subject_lessons)
        completed_in_block = sum(
            1 for lesson in subject_lessons if getattr(lesson, "is_completed", False)
        )
        progress_percent = (
            int(round((completed_in_block / total_in_block) * 100))
            if total_in_block
            else 0
        )
        next_candidate = next(
            (
                lesson
                for lesson in subject_lessons
                if getattr(lesson, "is_accessible", False)
                and not getattr(lesson, "is_completed", False)
            ),
            None,
        )
        if next_candidate is None and subject_lessons:
            next_candidate = subject_lessons[0]
        subject_blocks.append(
            {
                "title": subject.name,
                "slug": f"subject-{subject.id}",
                "description": subject.description,
                "lessons": subject_lessons,
                "completed": completed_in_block,
                "total": total_in_block,
                "progress_percent": progress_percent,
                "type": "subject",
                "subject": subject,
                "next_lesson": next_candidate,
            }
        )

    subject_blocks.sort(key=lambda block: block["title"].lower())
    lesson_blocks = path_blocks + subject_blocks
    return lesson_blocks
