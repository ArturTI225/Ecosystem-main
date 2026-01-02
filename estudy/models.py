from typing import Optional

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# 'timedelta' import removed; it was unused


def default_empty_list():
    return []


def default_empty_dict():
    return {}


class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Skill(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("title",)

    def __str__(self) -> str:
        return self.title


def default_theory_takeaways():
    return []


class Lesson(models.Model):
    DIFFICULTY_BEGINNER = "beginner"
    DIFFICULTY_INTERMEDIATE = "intermediate"
    DIFFICULTY_ADVANCED = "advanced"

    DIFFICULTY_CHOICES = [
        (DIFFICULTY_BEGINNER, "Beginner"),
        (DIFFICULTY_INTERMEDIATE, "Intermediate"),
        (DIFFICULTY_ADVANCED, "Advanced"),
    ]

    AGE_8_10 = "8-10"
    AGE_11_13 = "11-13"
    AGE_14_16 = "14-16"
    AGE_16_PLUS = "16+"

    AGE_BRACKET_CHOICES = [
        (AGE_8_10, _("8-10 ani")),
        (AGE_11_13, _("11-13 ani")),
        (AGE_14_16, _("14-16 ani")),
        (AGE_16_PLUS, _("16+ ani")),
    ]

    LESSON_TYPE_STANDARD = "standard"
    LESSON_TYPE_INTERACTIVE = "interactive"
    LESSON_TYPE_PROJECT = "project"
    LESSON_TYPE_QUIZ = "quiz"

    LESSON_TYPE_CHOICES = [
        (LESSON_TYPE_STANDARD, _("Standard")),
        (LESSON_TYPE_INTERACTIVE, _("Interactive")),
        (LESSON_TYPE_PROJECT, _("Project")),
        (LESSON_TYPE_QUIZ, _("Quiz")),
    ]

    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="lessons"
    )
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True, null=True)
    excerpt = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    date = models.DateField()
    duration_minutes = models.PositiveIntegerField(default=45)
    difficulty = models.CharField(
        max_length=20, choices=DIFFICULTY_CHOICES, default=DIFFICULTY_BEGINNER
    )
    lesson_type = models.CharField(
        max_length=20, choices=LESSON_TYPE_CHOICES, default=LESSON_TYPE_STANDARD
    )
    cover_image = models.ImageField(upload_to="lessons/covers/", blank=True, null=True)
    age_bracket = models.CharField(
        max_length=20, choices=AGE_BRACKET_CHOICES, default=AGE_11_13
    )
    theory_intro = models.TextField(blank=True)
    theory_takeaways = models.JSONField(default=default_theory_takeaways, blank=True)
    warmup_prompt = models.TextField(blank=True)
    discussion_prompts = models.JSONField(default=default_empty_list, blank=True)
    story_anchor = models.CharField(max_length=140, blank=True)
    home_extension = models.TextField(blank=True)
    collaboration_mode = models.CharField(
        max_length=30,
        choices=[
            ("solo", "Individual"),
            ("pairs", "În perechi"),
            ("small_group", "În echipe mici"),
            ("whole_class", "Împreună cu clasa"),
        ],
        default="solo",
    )
    content_tracks = models.JSONField(default=default_empty_list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    xp_reward = models.PositiveIntegerField(
        default=50, validators=[MinValueValidator(0), MaxValueValidator(500)]
    )
    fun_fact = models.TextField(blank=True)
    featured = models.BooleanField(default=False)
    hero_theme = models.CharField(max_length=60, default="sky-fizz")
    hero_emoji = models.CharField(max_length=10, default="🚀")
    skills = models.ManyToManyField(Skill, blank=True, related_name="lessons")

    class Meta:
        ordering = ("date", "title")

    def save(self, *args, **kwargs):
        defaults = self._build_default_meta()
        for field, value in defaults.items():
            setattr(self, field, value)
        if not self.slug:
            base_slug = slugify(self.title) or "lesson"
            slug = base_slug
            index = 1
            while Lesson.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                index += 1
                slug = f"{base_slug}-{index}"
            self.slug = slug
        super().save(*args, **kwargs)
        self._ensure_related_structures()

    def _build_default_meta(self) -> dict:
        prompts = [p.strip() for p in (self.discussion_prompts or []) if str(p).strip()]
        if not prompts:
            prompts = [
                f"Ce te surprinde la tema «{self.title}»?",
                "Cum ai explica această idee unui coleg mai mic?",
                "Unde ai întâlnit acest concept în viața de zi cu zi?",
            ]
        tracks = [t.strip() for t in (self.content_tracks or []) if str(t).strip()]
        if not tracks:
            tracks = ["Traseu de bază", "Bonus pentru exploratori"]
        data: dict[str, object] = {}
        if not self.warmup_prompt:
            data[
                "warmup_prompt"
            ] = f"Imaginează-ți că tema «{self.title}» te ajută într-o aventură. Cum ai folosi-o?"
        if not self.story_anchor:
            data[
                "story_anchor"
            ] = f"Astăzi explorăm tema «{self.title}» ca niște inventatori curioși."
        if not self.home_extension:
            data[
                "home_extension"
            ] = f"Povestește acasă ce ai învățat la lecția «{self.title}» și imaginați împreună o mini provocare."
        if not prompts or prompts != self.discussion_prompts:
            data["discussion_prompts"] = prompts
        if not tracks or tracks != self.content_tracks:
            data["content_tracks"] = tracks
        if not self.collaboration_mode:
            data["collaboration_mode"] = "small_group"
        return data

    def _ensure_related_structures(self) -> None:
        default_skills = [
            (
                "curiosity",
                "Curiozitate",
                "Învățăm să punem întrebări și să căutăm răspunsuri",
            ),
            (
                "creative-thinking",
                "Gândire creativă",
                "Găsim mai multe idei pentru aceeași provocare",
            ),
            (
                "communication",
                "Comunicare clară",
                "Ne exprimăm ideile pe înțelesul tuturor",
            ),
            (
                "problem-solving",
                "Rezolvare de probleme",
                "Împărțim sarcina în pași simpli și logici",
            ),
            (
                "digital-safety",
                "Siguranță digitală",
                "Lucrăm responsabil și protejat în mediul online",
            ),
        ]
        if not self.skills.exists():
            skill_objs = []
            for slug, title, description in default_skills:
                skill, _ = Skill.objects.get_or_create(
                    slug=slug, defaults={"title": title, "description": description}
                )
                skill_objs.append(skill)
            if skill_objs:
                index = (self.pk or 0) % len(skill_objs)
                to_assign = [
                    skill_objs[index],
                    skill_objs[(index + 1) % len(skill_objs)],
                ]
                self.skills.add(*to_assign)

        if not self.objectives.exists():
            objective_payloads = [
                (
                    f"Să descoperim cum se regăsește tema «{self.title}» în viața de zi cu zi.",
                    "Context",
                    "Pot să dau un exemplu din viața mea",
                ),
                (
                    "Să aplicăm noile cunoștințe într-o mini sarcină practică.",
                    "Practică",
                    "Rezolv pașii propuși și verific rezultatul",
                ),
                (
                    "Să formulăm un mesaj clar și să-l împărtășim cu colegii.",
                    "Comunicare",
                    "Explic ideea cu propriile cuvinte",
                ),
            ]
            LessonObjective.objects.bulk_create(
                [
                    LessonObjective(
                        lesson=self,
                        description=desc,
                        focus_area=focus,
                        success_criteria=criteria,
                        order=idx,
                    )
                    for idx, (desc, focus, criteria) in enumerate(objective_payloads)
                ]
            )

        if not self.reflection_prompts.exists():
            LessonReflectionPrompt.objects.bulk_create(
                [
                    LessonReflectionPrompt(
                        lesson=self,
                        prompt="Cum te simți după lecție?",
                        format=LessonReflectionPrompt.FORMAT_SCALE,
                        scale_labels=[
                            "Am nevoie de ajutor",
                            "Mă descurc",
                            "Pot explica și altora",
                        ],
                        order=0,
                    ),
                    LessonReflectionPrompt(
                        lesson=self,
                        prompt=f"Ce descoperire nouă ai făcut despre tema «{self.title}»?",
                        format=LessonReflectionPrompt.FORMAT_TEXT,
                        order=1,
                    ),
                ]
            )

        try:
            media = self.media
        except LessonMedia.DoesNotExist:
            media = None
        if media and not media.segments.exists():
            total = (
                media.video_duration_seconds
                or media.audio_duration_seconds
                or media.slides_count * 45
            )
            if total <= 0:
                total = 180
            checkpoints = [0]
            step = max(total // 3, 1)
            for idx in range(1, 3):
                checkpoints.append(min(step * idx, total))
            checkpoints.append(total)
            titles = [
                "Startul aventurii",
                "Misiunea practică",
                "Recapitulare și wow",
            ]
            segments = []
            for idx in range(3):
                segments.append(
                    LessonMediaSegment(
                        media=media,
                        title=titles[idx],
                        description=f"Segmentul {idx + 1} din lecția «{self.title}».",
                        start_seconds=checkpoints[idx],
                        end_seconds=checkpoints[idx + 1],
                        order=idx,
                    )
                )
            LessonMediaSegment.objects.bulk_create(segments)

    def get_resources_as_list(self) -> list[str]:
        """Return resource URLs for legacy template usage."""
        return [resource.url for resource in self.materials.all()]

    def get_absolute_url(self) -> str:
        return reverse("lesson_detail", args=[self.slug])

    @property
    def is_upcoming(self) -> bool:
        return self.date >= timezone.localdate()

    @property
    def difficulty_label(self) -> str:
        return dict(self.DIFFICULTY_CHOICES).get(self.difficulty, self.difficulty)

    @property
    def age_label(self) -> str:
        return dict(self.AGE_BRACKET_CHOICES).get(self.age_bracket, self.age_bracket)

    def theory_points(self) -> list[str]:
        return [
            item
            for item in self.theory_takeaways
            if isinstance(item, str) and item.strip()
        ]

    def difficulty_palette(self) -> dict[str, str]:
        return {
            "beginner": {
                "bg": "linear-gradient(135deg, #34d399, #10b981)",
                "accent": "#047857",
                "emoji": "🌱",
            },
            "intermediate": {
                "bg": "linear-gradient(135deg, #60a5fa, #2563eb)",
                "accent": "#1e3a8a",
                "emoji": "🚀",
            },
            "advanced": {
                "bg": "linear-gradient(135deg, #f59e0b, #f97316)",
                "accent": "#b45309",
                "emoji": "🧠",
            },
        }.get(
            self.difficulty,
            {
                "bg": "linear-gradient(135deg, #818cf8, #4f46e5)",
                "accent": "#312e81",
                "emoji": "✨",
            },
        )

    def __str__(self) -> str:
        return self.title


class LessonObjective(models.Model):
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="objectives"
    )
    description = models.CharField(max_length=255)
    focus_area = models.CharField(max_length=120, blank=True)
    success_criteria = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("lesson", "order", "id")

    def __str__(self) -> str:
        return f"{self.lesson.title} · {self.description[:50]}"


class LessonMedia(models.Model):
    """Resurse multimedia asociate lecției"""

    lesson = models.OneToOneField(
        Lesson, on_delete=models.CASCADE, related_name="media"
    )

    # Conținut video
    video_url = models.URLField(
        blank=True, help_text="URL-ul videoclipului (YouTube, Vimeo sau găzduit intern)"
    )
    video_platform = models.CharField(
        max_length=20,
        choices=[("youtube", "YouTube"), ("vimeo", "Vimeo"), ("self", "Self-hosted")],
        blank=True,
        help_text="Platforma pe care este găzduit videoclipul",
    )
    video_duration_seconds = models.PositiveIntegerField(
        default=0, help_text="Durata videoclipului în secunde"
    )
    video_thumbnail = models.ImageField(
        upload_to="videos/thumbnails/",
        blank=True,
        null=True,
        help_text="Imagine reprezentativă pentru videoclip",
    )

    # Conținut audio
    audio_url = models.URLField(blank=True, help_text="URL-ul fișierului audio")
    audio_duration_seconds = models.PositiveIntegerField(
        default=0, help_text="Durata audio în secunde"
    )

    # Prezentare
    slides_url = models.URLField(blank=True, help_text="URL-ul prezentării/slidelor")
    slides_count = models.PositiveIntegerField(
        default=0, help_text="Numărul de slide-uri din prezentare"
    )

    class Meta:
        verbose_name = "Lesson Media"
        verbose_name_plural = "Lesson Media"

    def __str__(self):
        return f"Media for {self.lesson.title}"


class LessonMediaSegment(models.Model):
    media = models.ForeignKey(
        LessonMedia, on_delete=models.CASCADE, related_name="segments"
    )
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    start_seconds = models.PositiveIntegerField(default=0)
    end_seconds = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("media", "order", "id")

    def __str__(self) -> str:
        return f"{self.media.lesson.title} · {self.title}"


class LessonResource(models.Model):
    TYPE_ARTICLE = "article"
    TYPE_VIDEO = "video"
    TYPE_WORKSHEET = "worksheet"
    TYPE_INTERACTIVE = "interactive"

    RESOURCE_TYPE_CHOICES = [
        (TYPE_ARTICLE, "Article"),
        (TYPE_VIDEO, "Video"),
        (TYPE_WORKSHEET, "Worksheet"),
        (TYPE_INTERACTIVE, "Interactive"),
    ]

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="materials"
    )
    title = models.CharField(max_length=150)
    url = models.URLField()
    resource_type = models.CharField(
        max_length=20, choices=RESOURCE_TYPE_CHOICES, default=TYPE_ARTICLE
    )
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self) -> str:
        return f"{self.lesson.title} · {self.title}"


class CodeExercise(models.Model):
    """Interactive code exercise linked to a lesson.

    Supports multiple languages (initially Python) and a simple JSON test suite.
    """

    LANG_PYTHON = "python"
    LANG_JS = "javascript"
    LANG_HTML = "html"
    LANG_SQL = "sql"

    LANGUAGE_CHOICES = [
        (LANG_PYTHON, "Python"),
        (LANG_JS, "JavaScript"),
        (LANG_HTML, "HTML/CSS"),
        (LANG_SQL, "SQL"),
    ]

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="code_exercises"
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    language = models.CharField(
        max_length=20, choices=LANGUAGE_CHOICES, default=LANG_PYTHON
    )
    starter_code = models.TextField(default="# Write your code here\n")
    solution = models.TextField(blank=True)
    hints = models.JSONField(default=default_empty_list, blank=True)
    # test_cases is a list of objects: {"input": "", "expected_output": "", "description": ""}
    test_cases = models.JSONField(default=default_empty_list, blank=True)
    difficulty_level = models.IntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    points = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("lesson", "order", "id")

    def __str__(self) -> str:
        return f"{self.lesson.title} · {self.title}"


class CodeSubmission(models.Model):
    """A user's attempt for a CodeExercise."""

    exercise = models.ForeignKey(
        CodeExercise, on_delete=models.CASCADE, related_name="submissions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="code_submissions"
    )
    code = models.TextField()

    # results
    passed_tests = models.PositiveIntegerField(default=0)
    total_tests = models.PositiveIntegerField(default=0)
    is_correct = models.BooleanField(default=False)
    execution_time_ms = models.PositiveIntegerField(default=0)
    output = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-submitted_at", "id")
        indexes = [
            models.Index(fields=["user", "exercise"], name="est_cs_user_ex_idx"),
        ]

    def __str__(self) -> str:
        status = "OK" if self.is_correct else "Fail"
        return f"{self.user.username} · {self.exercise.title} · {status}"


class UserProfile(models.Model):
    ROLE_STUDENT = "student"
    ROLE_PROFESSOR = "professor"
    ROLE_ADMIN = "admin"
    ROLE_PARENT = "parent"

    STATUS_CHOICES = [
        (ROLE_STUDENT, "Student"),
        (ROLE_PROFESSOR, "Profesor"),
        (ROLE_ADMIN, "Administrator"),
        (ROLE_PARENT, "Parinte"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # index to speed up role-based queries (dashboards, permission checks)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=ROLE_STUDENT, db_index=True
    )

    display_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    mascot_slug = models.CharField(max_length=40, default="robo-fox")
    theme_slug = models.CharField(max_length=40, default="sunny")
    favorite_subject = models.ForeignKey(
        "Subject", on_delete=models.SET_NULL, blank=True, null=True, related_name="fans"
    )
    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    streak = models.PositiveIntegerField(default=0)
    last_activity_at = models.DateTimeField(blank=True, null=True)
    weekly_goal = models.PositiveIntegerField(default=3)
    notifications_enabled = models.BooleanField(default=True)
    parent_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self) -> str:
        return self.user.username

    def role_label(self) -> str:
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    def is_student(self) -> bool:
        return self.status == self.ROLE_STUDENT

    def is_teacher(self) -> bool:
        return self.status == self.ROLE_PROFESSOR

    def is_admin(self) -> bool:
        return self.status == self.ROLE_ADMIN

    def is_parent(self) -> bool:
        return self.status == self.ROLE_PARENT

    def display_or_username(self) -> str:
        return self.display_name or self.user.get_short_name() or self.user.username

    def next_level_xp(self) -> int:
        return 100 + (self.level**2) * 25

    def add_xp(self, amount: int, reason: str = "") -> None:
        if amount <= 0:
            return
        self.xp += amount
        leveled_up = False
        while self.xp >= self.next_level_xp():
            self.level += 1
            leveled_up = True
        self.last_activity_at = timezone.now()
        self.save(update_fields=["xp", "level", "last_activity_at"])
        ExperienceLog.objects.create(
            user=self.user, amount=amount, reason=reason or "XP update"
        )
        if leveled_up:
            Notification.objects.create(
                recipient=self.user,
                title="Yay! Ai urcat de nivel",
                message=f"Bravo! Acum esti la nivelul {self.level}. Continua aventura.",
                category=Notification.CATEGORY_PROGRESS,
            )

    def progress_to_next_level(self) -> float:
        previous_threshold = 100 + ((self.level - 1) ** 2) * 25
        target = self.next_level_xp()
        if target <= previous_threshold:
            return 0.0
        return max(
            0.0,
            min(
                100.0,
                ((self.xp - previous_threshold) / (target - previous_threshold)) * 100,
            ),
        )


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = UserProfile.objects.create(user=instance)
        NotificationPreference.objects.get_or_create(user=instance)
        return profile
    instance.userprofile.save()


class ExperienceLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="xp_logs")
    amount = models.IntegerField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    time_taken_ms = models.PositiveIntegerField(default=0)
    awarded_points = models.PositiveIntegerField(default=0)
    earned_bonus = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user.username} +{self.amount} XP"


class LessonProgress(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_progress"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="progress_records"
    )
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    points_earned = models.PositiveIntegerField(default=0)
    fastest_completion_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "lesson")
        indexes = [
            models.Index(fields=["user", "completed"], name="est_lp_user_comp_idx"),
        ]

    def __str__(self) -> str:
        status = "Completed" if self.completed else "In progress"
        return f"{self.user.username} · {self.lesson.title} · {status}"

    def mark_completed(
        self, *, seconds_spent: Optional[int] = None, award_xp: bool = True
    ) -> None:
        already_completed = self.completed
        if not already_completed:
            self.completed = True
        if not self.completed_at:
            self.completed_at = timezone.now()
        update_fields = ["completed", "completed_at", "updated_at"]
        if seconds_spent is not None:
            if (
                self.fastest_completion_seconds == 0
                or seconds_spent < self.fastest_completion_seconds
            ):
                self.fastest_completion_seconds = seconds_spent
                update_fields.append("fastest_completion_seconds")
        xp_awarded = 0
        if award_xp and not already_completed and hasattr(self.user, "userprofile"):
            xp_awarded = self.lesson.xp_reward
            self.user.userprofile.add_xp(
                xp_awarded, reason=f"Lesson {self.lesson.title} completed"
            )
        if xp_awarded and xp_awarded > self.points_earned:
            self.points_earned = xp_awarded
            if "points_earned" not in update_fields:
                update_fields.append("points_earned")
        self.save(update_fields=update_fields)

    def toggle(self, award_xp: bool = True) -> None:
        if self.completed:
            self.completed = False
            self.completed_at = None
            self.save(update_fields=["completed", "completed_at", "updated_at"])
        else:
            # delegate to mark_completed to ensure XP, streaks, etc. are awarded once
            self.mark_completed(award_xp=award_xp)


class VideoProgress(models.Model):
    """Progress tracking for video content in lessons"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="video_progress"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="video_progress"
    )
    watched_seconds = models.PositiveIntegerField(default=0)
    completion_percent = models.FloatField(
        default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    last_position = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "lesson")
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} video progress"


class LessonPersonalization(models.Model):
    """Personalization settings for lessons per user"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_personalizations"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="personalizations"
    )

    # Display settings
    show_hints = models.BooleanField(default=True)
    show_extra_examples = models.BooleanField(default=False)
    content_difficulty = models.CharField(
        max_length=20, choices=Lesson.DIFFICULTY_CHOICES, default="intermediate"
    )

    # Pace settings
    estimated_time_minutes = models.PositiveIntegerField(default=45)
    actual_time_minutes = models.PositiveIntegerField(default=0)

    # Media preferences
    preferred_media = models.CharField(
        max_length=20,
        choices=[("text", "Text"), ("video", "Video"), ("mixed", "Mixed")],
        default="mixed",
    )

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user.username} - {self.lesson.title} personalization"


class LessonModule(models.Model):
    """Micro-learning module within a lesson"""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=150)
    content = models.TextField()

    module_type = models.CharField(
        max_length=20,
        choices=[
            ("concept", "Concept"),
            ("example", "Example"),
            ("practice", "Practice"),
            ("quiz", "Mini-quiz"),
        ],
        default="concept",
    )

    duration_minutes = models.PositiveIntegerField(default=5)
    order = models.PositiveIntegerField(default=0)

    # Dependencies
    requires_modules = models.ManyToManyField("self", symmetrical=False, blank=True)

    class Meta:
        ordering = ["lesson", "order"]

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class ModuleProgress(models.Model):
    """Progress tracking for lesson modules"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="module_progress"
    )
    module = models.ForeignKey(
        LessonModule, on_delete=models.CASCADE, related_name="progress_records"
    )

    viewed = models.BooleanField(default=False)
    understood = models.BooleanField(default=False)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    quiz_score = models.FloatField(
        default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "module")
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} - {self.module.title} progress"


class Reward(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="rewards/", blank=True, null=True)

    def __str__(self) -> str:
        return self.name


class UserReward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rewards")
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    date_awarded = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.user.username} · {self.reward.name}"


class Badge(models.Model):
    RULE_LESSONS = "lessons_completed"
    RULE_STREAK = "quiz_streak"
    RULE_SPEED = "fast_finisher"
    RULE_PROJECT = "project_submitted"
    RULE_CHALLENGE = "challenge_master"

    RULE_CHOICES = [
        (RULE_LESSONS, "Lessons completed"),
        (RULE_STREAK, "Quiz streak"),
        (RULE_SPEED, "Fast finisher"),
        (RULE_PROJECT, "Project submitted"),
        (RULE_CHALLENGE, "Challenge master"),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, default="fa-star")
    color = models.CharField(max_length=20, default="#2563eb")
    rule = models.CharField(max_length=40, choices=RULE_CHOICES, blank=True)
    threshold = models.PositiveIntegerField(default=0)
    xp_reward = models.PositiveIntegerField(default=50)
    is_secret = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    time_taken_ms = models.PositiveIntegerField(default=0)
    awarded_points = models.PositiveIntegerField(default=0)
    earned_bonus = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="badge_awards"
    )
    badge = models.ForeignKey("Badge", on_delete=models.CASCADE, related_name="awards")
    awarded_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=60, blank=True)

    class Meta:
        unique_together = ("user", "badge")
        ordering = ("-awarded_at",)

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.badge.name}"


class Mission(models.Model):
    FREQ_DAILY = "daily"
    FREQ_WEEKLY = "weekly"
    FREQ_ONCE = "once"

    FREQUENCY_CHOICES = [
        (FREQ_DAILY, "Daily"),
        (FREQ_WEEKLY, "Weekly"),
        (FREQ_ONCE, "One time"),
    ]

    code = models.SlugField(unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    frequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default=FREQ_DAILY
    )
    target_value = models.PositiveIntegerField(default=1)
    reward_points = models.PositiveIntegerField(default=50)
    reward_badge = models.ForeignKey(
        "Badge", on_delete=models.SET_NULL, blank=True, null=True
    )
    icon = models.CharField(max_length=40, default="fa-rocket")
    color = models.CharField(max_length=20, default="#6366f1")
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class UserMission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="missions")
    mission = models.ForeignKey(
        "Mission", on_delete=models.CASCADE, related_name="states"
    )
    progress = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_reset = models.DateField(blank=True, null=True)

    class Meta:
        unique_together = ("user", "mission")

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.mission.code}"

    def register_progress(self) -> None:
        """Increment progress and check for completion."""
        # Reset progress if needed based on frequency
        today = timezone.localdate()
        if self.mission.frequency == Mission.FREQ_DAILY:
            if self.last_reset != today:
                self.progress = 0
                self.completed = False
                self.completed_at = None
                self.last_reset = today
        elif self.mission.frequency == Mission.FREQ_WEEKLY:
            # Reset on Monday (weekday 0)
            if today.weekday() == 0 and (
                self.last_reset is None or self.last_reset < today
            ):
                self.progress = 0
                self.completed = False
                self.completed_at = None
                self.last_reset = today

        # Increment progress
        self.progress += 1

        # Check for completion
        if not self.completed and self.progress >= self.mission.target_value:
            self.completed = True
            self.completed_at = timezone.now()

        self.save()


class LessonChallenge(models.Model):
    """Challenge within a lesson for gamification"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="challenges"
    )
    title = models.CharField(max_length=150)
    description = models.TextField()

    challenge_type = models.CharField(
        max_length=20,
        choices=[
            ("speed", "Speed"),
            ("accuracy", "Accuracy"),
            ("creativity", "Creativity"),
            ("combo", "Combo"),
        ],
        default="speed",
    )

    # Conditions
    target_time_seconds = models.PositiveIntegerField(default=300)
    target_accuracy = models.FloatField(
        default=90.0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Rewards
    badge = models.ForeignKey(
        "Badge",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lesson_challenges",
    )
    xp_reward = models.PositiveIntegerField(default=50)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class LessonStreak(models.Model):
    """Streak tracking for lesson completion"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_streaks"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, null=True, blank=True
    )

    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_lesson_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "subject")

    def __str__(self):
        subject_name = self.subject.name if self.subject else "All"
        return f"{self.user.username} - {subject_name} streak: {self.current_streak}"


class LessonEasterEgg(models.Model):
    """Hidden rewards (easter eggs) in lessons"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="easter_eggs"
    )
    trigger_condition = models.CharField(
        max_length=100, help_text="Condition to trigger the easter egg"
    )

    reward_type = models.CharField(
        max_length=20,
        choices=[("badge", "Badge"), ("xp", "XP"), ("unlock", "Unlock")],
        default="xp",
    )
    reward_value = models.PositiveIntegerField(default=0)
    message = models.TextField(help_text="Message shown when easter egg is found")

    def __str__(self):
        return f"{self.lesson.title} easter egg"


class LessonHint(models.Model):
    """Smart hints for lessons"""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="hints")
    section = models.CharField(
        max_length=100, help_text="Section of the lesson (theory, practice, test)"
    )

    hint_text = models.TextField()
    hint_level = models.IntegerField(
        default=1, help_text="1=easy, 2=medium, 3=full answer"
    )

    # Trigger conditions
    trigger_after_seconds = models.PositiveIntegerField(default=300)
    show_after_attempts = models.PositiveIntegerField(default=2)

    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["lesson", "section", "hint_level"]

    def __str__(self):
        return f"{self.lesson.title} - {self.section} hint (level {self.hint_level})"


class AIHintRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_requests")
    lesson = models.ForeignKey(
        "Lesson", on_delete=models.SET_NULL, blank=True, null=True
    )
    question = models.TextField()
    response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"AI request by {self.user.username}"


class AvatarUnlock(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="avatar_unlocks"
    )
    slug = models.CharField(max_length=60)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "slug")

    def __str__(self) -> str:
        return f"{self.user.username} unlocked {self.slug}"


class LeaderboardSnapshot(models.Model):
    PERIOD_WEEK = "week"
    PERIOD_MONTH = "month"

    period = models.CharField(
        max_length=10,
        choices=[(PERIOD_WEEK, "Week"), (PERIOD_MONTH, "Month")],
        default=PERIOD_WEEK,
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=default_empty_list, blank=True)

    class Meta:
        ordering = ("-generated_at",)

    def __str__(self) -> str:
        return f"Leaderboard {self.period}"


def check_and_award_rewards(user: User) -> None:
    completed_lessons = LessonProgress.objects.filter(user=user, completed=True).count()
    profile = getattr(user, "userprofile", None)

    milestones = [
        ("curious-coder", 3, "Curious Coder", "fa-lightbulb", "#22c55e"),
        ("fast-learner", 5, "Fast Learner", "fa-bolt", "#f97316"),
        ("lesson-explorer", 10, "Lesson Explorer", "fa-map", "#6366f1"),
        ("learning-legend", 20, "Learning Legend", "fa-crown", "#a855f7"),
    ]

    for slug, threshold, name, icon, color in milestones:
        if completed_lessons < threshold:
            continue
        badge, _ = Badge.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": f"Completed {threshold} lessons",
                "icon": icon,
                "color": color,
                "rule": Badge.RULE_LESSONS,
                "threshold": threshold,
                "xp_reward": 40 + threshold * 4,
            },
        )
        award, created = UserBadge.objects.get_or_create(
            user=user,
            badge=badge,
            defaults={"reason": f"Completed {threshold} lessons"},
        )
        if created:
            if profile:
                profile.add_xp(badge.xp_reward, reason=f"Badge {badge.name}")
            Notification.objects.create(
                recipient=user,
                title=f"Ai castigat insigna {badge.name}!",
                message=f"Tine-o tot asa, ai atins pragul de {threshold} lectii.",
                category=Notification.CATEGORY_PROGRESS,
            )

    if completed_lessons >= 10:
        reward, _ = Reward.objects.get_or_create(
            name="10 Lessons Complete",
            defaults={"description": "Completed ten lessons."},
        )
        UserReward.objects.get_or_create(user=user, reward=reward)

    if profile:
        profile.streak += 1
        profile.last_activity_at = timezone.now()
        profile.save(update_fields=["streak", "last_activity_at"])


class Test(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="tests")
    question = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=255)
    wrong_answers = models.JSONField()
    theory_summary = models.TextField(blank=True)
    practice_prompt = models.TextField(blank=True)
    explanation = models.TextField(blank=True)

    difficulty = models.CharField(
        max_length=20,
        choices=Lesson.DIFFICULTY_CHOICES,
        default=Lesson.DIFFICULTY_BEGINNER,
    )
    time_limit_seconds = models.PositiveIntegerField(default=60)
    points = models.PositiveIntegerField(default=100)
    bonus_time_threshold = models.PositiveIntegerField(default=20)

    def __str__(self) -> str:
        return self.question

    def answer_choices(self) -> list[str]:
        return [self.correct_answer, *self.wrong_answers]


class TestAttempt(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="attempts")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="test_attempts"
    )
    selected_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    time_taken_ms = models.PositiveIntegerField(default=0)
    awarded_points = models.PositiveIntegerField(default=0)
    earned_bonus = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user.username} · {self.test.question[:30]}..."


def default_practice_data() -> dict[str, list]:
    return {"draggables": [], "targets": []}


class LessonPractice(models.Model):
    lesson = models.OneToOneField(
        Lesson, on_delete=models.CASCADE, related_name="practice"
    )
    intro = models.TextField(blank=True)
    instructions = models.CharField(max_length=200, blank=True)
    success_message = models.CharField(
        max_length=150, default="Super! Ai reușit să potrivești corect."
    )
    data = models.JSONField(default=default_practice_data, blank=True)

    def __str__(self) -> str:
        return f"Practice · {self.lesson.title}"

    @property
    def has_pairs(self) -> bool:
        draggables = (
            self.data.get("draggables", []) if isinstance(self.data, dict) else []
        )
        targets = self.data.get("targets", []) if isinstance(self.data, dict) else []
        return bool(draggables and targets)


class LessonReflectionPrompt(models.Model):
    FORMAT_TEXT = "text"
    FORMAT_SCALE = "scale"
    FORMAT_DRAW = "draw"

    FORMAT_CHOICES = [
        (FORMAT_TEXT, "Open response"),
        (FORMAT_SCALE, "Rating scale"),
        (FORMAT_DRAW, "Creative"),
    ]

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="reflection_prompts"
    )
    prompt = models.CharField(max_length=255)
    format = models.CharField(
        max_length=20, choices=FORMAT_CHOICES, default=FORMAT_TEXT
    )
    order = models.PositiveIntegerField(default=0)
    scale_labels = models.JSONField(default=default_empty_list, blank=True)

    class Meta:
        ordering = ("lesson", "order", "id")

    def __str__(self) -> str:
        return f"{self.lesson.title} · reflection"


class Notification(models.Model):
    CATEGORY_PROGRESS = "progress"
    CATEGORY_FEEDBACK = "feedback"
    CATEGORY_SYSTEM = "system"
    CATEGORY_COMMUNITY = "community"

    CATEGORY_CHOICES = [
        (CATEGORY_PROGRESS, "Progress"),
        (CATEGORY_FEEDBACK, "Feedback"),
        (CATEGORY_SYSTEM, "System"),
        (CATEGORY_COMMUNITY, "Community"),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_SYSTEM
    )
    link_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["recipient", "read_at"], name="est_not_rec_read_idx"),
        ]

    def __str__(self) -> str:
        return f"Notification for {self.recipient.username}: {self.title}"

    def mark_as_read(self) -> None:
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class NotificationPreference(models.Model):
    DIGEST_DAILY = "daily"
    DIGEST_WEEKLY = "weekly"
    DIGEST_NEVER = "never"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )
    email_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            (DIGEST_DAILY, "Daily"),
            (DIGEST_WEEKLY, "Weekly"),
            (DIGEST_NEVER, "Never"),
        ],
        default=DIGEST_WEEKLY,
    )

    def __str__(self) -> str:
        return f"Preferences for {self.user.username}"


class LessonFeedback(models.Model):
    """Feedback and ratings for lessons"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="feedbacks"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_feedbacks"
    )

    # Ratings (1-5)
    content_quality = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    difficulty_appropriate = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    examples_helpful = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    overall_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    # Comments
    what_worked = models.TextField(blank=True)
    what_didnt_work = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)

    # Additional
    would_recommend = models.BooleanField(default=True)
    time_to_complete = models.PositiveIntegerField(
        default=0, help_text="Time to complete in minutes"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("lesson", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback for {self.lesson.title} by {self.user.username}"


class LessonSection(models.Model):
    """Progressive content sections within a lesson"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="sections"
    )
    title = models.CharField(max_length=150)
    content = models.TextField()

    section_type = models.CharField(
        max_length=20,
        choices=[
            ("introduction", "Introduction"),
            ("theory", "Theory"),
            ("example", "Examples"),
            ("practice", "Practice"),
            ("summary", "Summary"),
        ],
        default="theory",
    )

    order = models.PositiveIntegerField(default=0)

    # Unlock conditions
    requires_previous_complete = models.BooleanField(default=True)
    unlock_after_seconds = models.PositiveIntegerField(default=0)

    # Comprehension check
    comprehension_quiz = models.JSONField(
        default=list, help_text="Mini-questions to check understanding"
    )

    class Meta:
        ordering = ["lesson", "order"]

    def __str__(self):
        return f"{self.lesson.title} - {self.title}"


class SectionProgress(models.Model):
    """Progress tracking for lesson sections"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="section_progress"
    )
    section = models.ForeignKey(
        LessonSection, on_delete=models.CASCADE, related_name="progress_records"
    )

    viewed = models.BooleanField(default=False)
    understood = models.BooleanField(default=False)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    quiz_score = models.FloatField(
        default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "section")
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} - {self.section.title} progress"


class LessonDownload(models.Model):
    """Offline lesson downloads for PWA"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_downloads"
    )
    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="downloads"
    )

    downloaded_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When the download expires")

    # Cached content
    cached_content = models.JSONField(default=dict)
    cached_media_urls = models.JSONField(default=list)

    file_size_mb = models.FloatField(default=0)

    class Meta:
        unique_together = ("user", "lesson")
        ordering = ["-downloaded_at"]

    def __str__(self):
        return f"{self.user.username} downloaded {self.lesson.title}"


class LearningPath(models.Model):
    title = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    theme = models.CharField(max_length=40, default="rainbow")
    difficulty = models.CharField(
        max_length=20,
        choices=Lesson.DIFFICULTY_CHOICES,
        default=Lesson.DIFFICULTY_BEGINNER,
    )
    audience = models.CharField(max_length=60, default="general")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    time_taken_ms = models.PositiveIntegerField(default=0)
    awarded_points = models.PositiveIntegerField(default=0)
    earned_bonus = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ("title",)

    def __str__(self):
        return self.title


class LearningPathLesson(models.Model):
    path = models.ForeignKey(
        "LearningPath", on_delete=models.CASCADE, related_name="items"
    )
    lesson = models.ForeignKey(
        "Lesson", on_delete=models.CASCADE, related_name="path_items"
    )
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("order",)
        unique_together = ("path", "lesson")

    def __str__(self):
        return f"{self.path.title} -> {self.lesson.title}"


class LearningRecommendation(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recommendations"
    )
    lesson = models.ForeignKey("Lesson", on_delete=models.CASCADE)
    reason = models.CharField(max_length=255)
    score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed = models.BooleanField(default=False)

    class Meta:
        ordering = ("-score", "-created_at")
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.lesson.title}"


class LessonComment(models.Model):
    """Comments and discussions on lessons"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_comments"
    )

    content = models.TextField()
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies"
    )

    # Moderation
    is_approved = models.BooleanField(default=True)
    is_hidden = models.BooleanField(default=False)

    # Engagement
    likes_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["lesson", "created_at"], name="lesson_comments_idx"),
            models.Index(fields=["parent", "created_at"], name="comment_replies_idx"),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.lesson.title}"

    @property
    def is_reply(self):
        return self.parent is not None


class CommentLike(models.Model):
    """Likes for lesson comments"""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="comment_likes"
    )
    comment = models.ForeignKey(
        LessonComment, on_delete=models.CASCADE, related_name="likes"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "comment")

    def __str__(self):
        return f"{self.user.username} liked comment {self.comment.id}"


class LessonRating(models.Model):
    """Star ratings for lessons"""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="lesson_ratings"
    )

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("lesson", "user")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} rated {self.lesson.title}: {self.rating} stars"


class LessonAnalytics(models.Model):
    """Analytics data for lesson performance"""

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="analytics"
    )
    date = models.DateField()

    # Engagement metrics
    views = models.PositiveIntegerField(default=0)
    unique_views = models.PositiveIntegerField(default=0)
    completions = models.PositiveIntegerField(default=0)

    # Time metrics
    avg_time_spent = models.PositiveIntegerField(
        default=0, help_text="Average time spent in seconds"
    )
    median_time_spent = models.PositiveIntegerField(
        default=0, help_text="Median time spent in seconds"
    )

    # Performance metrics
    avg_score = models.FloatField(
        default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    completion_rate = models.FloatField(
        default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Drop-off analysis
    drop_off_points = models.JSONField(
        default=dict, help_text="Where students drop off (section -> count)"
    )

    # Social metrics
    comments_count = models.PositiveIntegerField(default=0)
    ratings_count = models.PositiveIntegerField(default=0)
    avg_rating = models.FloatField(
        default=0.0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    # Technical metrics
    error_count = models.PositiveIntegerField(default=0)
    load_time_avg = models.PositiveIntegerField(
        default=0, help_text="Average load time in ms"
    )

    class Meta:
        unique_together = ("lesson", "date")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["lesson", "date"], name="lesson_analytics_idx"),
        ]

    def __str__(self):
        return f"Analytics for {self.lesson.title} on {self.date}"

    def engagement_rate(self):
        """Rate of unique views that lead to completion"""
        if self.unique_views == 0:
            return 0.0
        return (self.completions / self.unique_views) * 100


# Temporary placeholder models for dashboard functionality
# TODO: Implement full functionality later


class Project(models.Model):
    """Placeholder for Project model"""

    title = models.CharField(max_length=200)
    level = models.IntegerField(default=1)

    def __str__(self):
        return self.title


class ProjectSubmission(models.Model):
    """Placeholder for ProjectSubmission model"""

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.project.title}"


class DailyChallenge(models.Model):
    """Placeholder for DailyChallenge model"""

    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.title
