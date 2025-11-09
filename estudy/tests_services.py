from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import (LearningPath, LearningPathLesson, LearningRecommendation,
                     Lesson, LessonProgress, Subject)
from .services.dashboard import build_student_dashboard
from .services.gamification import build_overall_progress
from .services.lesson_detail import build_lesson_detail_payload
from .services.lessons import build_lesson_blocks
from .services.recommendations import (calculate_recommendations,
                                       refresh_recommendations)
from .services.lessons import prepare_lessons_list


class ServicesSmokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="pw")
        # create subject + lessons
        self.subject = Subject.objects.create(name="Math", description="Numbers")
        today = timezone.localdate()
        self.lessons = []
        for i in range(3):
            lesson = Lesson.objects.create(
                subject=self.subject,
                title=f"Lesson {i + 1}",
                content="content",
                date=today,
            )
            self.lessons.append(lesson)

        # learning path with first two lessons
        self.path = LearningPath.objects.create(
            title="Path 1", slug="path-1", description="p", theme="t"
        )
        LearningPathLesson.objects.create(
            path=self.path, lesson=self.lessons[0], order=1
        )
        LearningPathLesson.objects.create(
            path=self.path, lesson=self.lessons[1], order=2
        )

    def test_build_lesson_blocks_and_detail_payload(self):
        # mark first as completed and accessible
        completed_ids = {self.lessons[0].id}
        accessible_ids = {lesson.id for lesson in self.lessons}
        # set attributes used by the service (not DB fields)
        for lesson in self.lessons:
            setattr(lesson, "is_completed", lesson.id in completed_ids)
            setattr(lesson, "is_accessible", lesson.id in accessible_ids)
            setattr(lesson, "sequence", {"index": 1})

        blocks = build_lesson_blocks(
            [self.subject], self.lessons, completed_ids, accessible_ids, [self.path]
        )
        self.assertTrue(any(b.get("type") == "path" for b in blocks))
        self.assertTrue(any(b.get("type") == "subject" for b in blocks))

        payload = build_lesson_detail_payload(
            self.user,
            self.lessons[1],
            list(self.subject.lessons.all()),
            1,
            {self.lessons[0].id},
            {},
        )
        self.assertIn("lesson_position", payload)
        self.assertIn("lesson_materials", payload)
        self.assertEqual(payload["lesson_position"], 2)

    def test_calculate_and_refresh_recommendations(self):
        # mark the first lesson as completed
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[0], completed=True
        )
        recs = calculate_recommendations(self.user, limit=2)
        self.assertIsInstance(recs, list)
        # refresh should create LearningRecommendation objects
        rec_objs = refresh_recommendations(self.user, limit=2)
        self.assertTrue(all(isinstance(r, LearningRecommendation) for r in rec_objs))
        self.assertEqual(
            LearningRecommendation.objects.filter(user=self.user).count(), len(rec_objs)
        )

    def test_build_overall_progress_and_dashboard(self):
        # create 4 lessons total to compute percent
        today = timezone.localdate()
        extra = []
        for i in range(1):
            extra_l = Lesson.objects.create(
                subject=self.subject, title=f"Extra {i}", content="c", date=today
            )
            extra.append(extra_l)
        # mark one completed
        LessonProgress.objects.create(
            user=self.user, lesson=self.lessons[0], completed=True
        )
        progress = build_overall_progress(self.user)
        self.assertIn("percent", progress)
        dashboard = build_student_dashboard(self.user)
        self.assertIn("progress", dashboard)
        self.assertEqual(dashboard["progress"]["percent"], progress["percent"])

    def test_prepare_lessons_list_service(self):
        # ensure the service returns expected keys and respects defaults
        ctx = prepare_lessons_list(self.user, params=None)
        self.assertIsInstance(ctx, dict)
        for key in (
            "subjects",
            "lessons",
            "lesson_blocks",
            "filters",
            "badge_summary",
        ):
            self.assertIn(key, ctx)
        # default filters should be empty/false
        self.assertEqual(ctx["filters"]["query"], "")
        self.assertEqual(ctx["filters"]["subject"], "")
        self.assertEqual(ctx["filters"]["difficulty"], "")
        self.assertFalse(ctx["filters"]["upcoming"])
