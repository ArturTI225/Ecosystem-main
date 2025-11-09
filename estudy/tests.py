from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Lesson, LessonProgress, Subject


class LessonViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", email="t@example.com", password="pass1234"
        )
        self.client.login(username="tester", password="pass1234")
        self.subject = Subject.objects.create(name="Test Subject")

    def _create_lesson(self, title, days_offset=0):
        date = timezone.localdate() + timezone.timedelta(days=days_offset)
        lesson = Lesson.objects.create(
            subject=self.subject,
            title=title,
            content="Content",
            date=date,
        )
        return lesson

    def test_lesson_detail_redirects_if_previous_not_completed(self):
        # create two lessons in sequence: older (required) and newer
        l1 = self._create_lesson("First", days_offset=-2)
        l2 = self._create_lesson("Second", days_offset=0)

        url = reverse("estudy:lesson_detail", kwargs={"slug": l2.slug})
        resp = self.client.get(url)
        # should redirect to the blocking lesson (first)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(l1.slug, resp.url)

    def test_toggle_lesson_completion_marks_completed(self):
        lesson = self._create_lesson("Solo", days_offset=0)
        url = reverse("estudy:toggle_lesson_completion", kwargs={"slug": lesson.slug})
        resp = self.client.post(url, {"seconds": "45"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("completed"))
        self.assertIn("progress_percent", data)
        # verify LessonProgress exists and is completed
        progress = LessonProgress.objects.filter(user=self.user, lesson=lesson).first()
        self.assertIsNotNone(progress)
        self.assertTrue(progress.completed)


class ModelsLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="muser", email="m@example.com", password="pass1234"
        )
        # ensure profile created by signal
        self.profile = self.user.userprofile
        self.subject = Subject.objects.create(name="Logic Subject")

    def test_lessonprogress_mark_completed_awards_xp_and_points(self):
        lesson = Lesson.objects.create(
            subject=self.subject, title="L1", content="C", date=timezone.localdate()
        )
        progress = LessonProgress.objects.create(user=self.user, lesson=lesson)
        # initial xp
        initial_xp = self.profile.xp
        progress.mark_completed(seconds_spent=42)
        progress.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertTrue(progress.completed)
        self.assertIsNotNone(progress.completed_at)
        self.assertGreaterEqual(progress.points_earned, lesson.xp_reward)
        self.assertGreaterEqual(self.profile.xp, initial_xp + lesson.xp_reward)

    def test_userprofile_add_xp_levels_up_and_logs(self):
        initial_level = self.profile.level
        # give enough xp to level up multiple times
        self.profile.add_xp(300, reason="test XP")
        self.profile.refresh_from_db()
        # level should have increased at least once
        self.assertGreater(self.profile.level, initial_level)
        # ExperienceLog should be created
        from .models import ExperienceLog

        self.assertTrue(ExperienceLog.objects.filter(user=self.user).exists())

    def test_check_and_award_rewards_creates_badges_and_rewards(self):
        # create multiple lessons and mark them completed
        lessons = []
        for i in range(12):
            lesson = Lesson.objects.create(
                subject=self.subject,
                title=f"L{i}",
                content="C",
                date=timezone.localdate(),
            )
            lessons.append(lesson)
            LessonProgress.objects.create(
                user=self.user,
                lesson=lesson,
                completed=True,
                completed_at=timezone.now(),
            )

        # ensure no badges initially
        from .models import Reward, UserBadge, UserReward

        UserBadge.objects.filter(user=self.user).delete()
        UserReward.objects.filter(user=self.user).delete()

        # run the checker
        from .models import check_and_award_rewards

        check_and_award_rewards(self.user)
        # badges should be awarded
        self.assertTrue(UserBadge.objects.filter(user=self.user).exists())
        # reward for 10 lessons
        self.assertTrue(Reward.objects.filter(name__icontains="10 Lessons").exists())
        self.assertTrue(UserReward.objects.filter(user=self.user).exists())
        # profile streak and last_activity_at updated
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.last_activity_at)
        self.assertGreaterEqual(self.profile.streak, 1)
