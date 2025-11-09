from __future__ import annotations

from typing import Iterable

from django.utils import timezone

from ..models import AIHintRequest


def _clean_snippets(items: Iterable[str]) -> list[str]:
    return [item.strip() for item in items if item and item.strip()]


def _keyword_hint(question: str) -> str | None:
    q = question.lower()
    keyword_tips = [
        (("variabil", "variabile"), "Imaginează-ți variabilele ca pe niște cutii cu etichete. Pune o valoare clară în cutie și folosește exact același nume când ai nevoie de ea."),
        (("loop", "bucl", "repet"), "Stabilește ce se schimbă la fiecare iterație și ce condiție oprește bucla. Scrie acea condiție înainte de cod."),
        (("condit", "if", "else"), "Formulează propoziția „Dacă ... atunci ... altfel ...” în română și abia apoi trad-o în if/else."),
        (("lista", "array"), "Gândește-te la liste ca la rafturi numerotate. Indicii pornesc de la 0, deci elementul al treilea are index 2."),
    ]
    for keywords, tip in keyword_tips:
        if any(word in q for word in keywords):
            return tip
    return None


def _lesson_clues(lesson) -> list[str]:
    if not lesson:
        return []

    clues: list[str] = []

    intro = (lesson.theory_intro or lesson.excerpt or "").strip()
    if intro:
        clues.append(intro)

    theory_takeaways = _clean_snippets(getattr(lesson, "theory_takeaways", []))
    method_takeaways = _clean_snippets(lesson.theory_points())
    clues.extend(theory_takeaways or method_takeaways)

    practice = getattr(lesson, "practice", None)
    if practice:
        clues.extend(_clean_snippets([practice.instructions, practice.intro]))

    return clues[:4]


def _build_answer(question: str, lesson) -> str:
    user_question = question.strip() or "Am nevoie de un indiciu."
    keyword_tip = _keyword_hint(user_question)
    lesson_clues = _lesson_clues(lesson)

    main_tip = keyword_tip or (
        lesson_clues[0] if lesson_clues else "Reia exemplul din secțiunea Concept și notează pașii pe scurt."
    )

    extra_tip = lesson_clues[1] if len(lesson_clues) > 1 else "Testează varianta ta în mini-editorul din Example și observă output-ul."

    next_step = "Intră în Practice și vezi dacă poți aplica imediat indiciul."
    if lesson and getattr(lesson, "practice", None):
        next_step = "În Practice, pornește de la hint-ul disponibil și potrivește elementele ținând cont de cuvintele cheie."
    if lesson and lesson.tests.exists():
        next_step += " Apoi revino la Test pentru a fixa ideea."

    lines = [
        f"Întrebare primită: „{user_question}”.",
        f"1) Hint rapid: {main_tip}",
        f"2) Mai încearcă: {extra_tip}",
        f"Pas următor: {next_step}",
    ]
    return "\n".join(lines)


def generate_hint(user, question: str, *, lesson=None) -> AIHintRequest:
    answer = _build_answer(question or "", lesson)
    request = AIHintRequest.objects.create(
        user=user,
        lesson=lesson,
        question=question,
        response=answer,
        resolved_at=timezone.now(),
    )
    return request
