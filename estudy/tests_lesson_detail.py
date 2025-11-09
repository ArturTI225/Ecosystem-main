from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from .models import Lesson, LessonProgress, Subject
from .services.lesson_detail import (BlockingLessonRequired,
                                     prepare_lesson_detail)


class LessonDetailServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ld", password="pw")
        self.subject = Subject.objects.create(name="S", description="D")
        today = timezone.localdate()
        self.l1 = Lesson.objects.create(
            subject=self.subject, title="L1", content="c", date=today
        )
        self.l2 = Lesson.objects.create(
            subject=self.subject, title="L2", content="c", date=today
        )

    def test_blocking_lesson_raises(self):
        # when accessing l2 without completing l1, expect BlockingLessonRequired
        with self.assertRaises(BlockingLessonRequired) as cm:
            prepare_lesson_detail(self.user, self.l2.slug)
        self.assertEqual(cm.exception.blocking_slug, self.l1.slug)

    def test_payload_when_no_block(self):
        # complete l1 then fetch l2
        LessonProgress.objects.create(user=self.user, lesson=self.l1, completed=True)
        payload = prepare_lesson_detail(self.user, self.l2.slug)
        self.assertIn("lesson", payload)
        self.assertIn("subject_sequence", payload)
        self.assertIn("lesson_position", payload)
        self.assertEqual(payload["lesson"].slug, self.l2.slug)
