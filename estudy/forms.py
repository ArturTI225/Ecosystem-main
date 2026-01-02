from django import forms

from .models import (
    Lesson,
    LessonMedia,
    LessonPractice,
    LessonResource,
    NotificationPreference,
    Test,
    UserProfile,
)


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = [
            "subject",
            "title",
            "excerpt",
            "content",
            "date",
            "duration_minutes",
            "difficulty",
            "lesson_type",
            "cover_image",
            "age_bracket",
            "theory_intro",
            "theory_takeaways",
            "xp_reward",
            "fun_fact",
            "featured",
            "hero_theme",
            "hero_emoji",
        ]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 10}),
            "theory_intro": forms.Textarea(attrs={"rows": 5}),
            "theory_takeaways": forms.Textarea(attrs={"rows": 5}),
            "fun_fact": forms.Textarea(attrs={"rows": 3}),
            "date": forms.DateInput(attrs={"type": "date"}),
        }


class LessonMediaForm(forms.ModelForm):
    class Meta:
        model = LessonMedia
        fields = [
            "video_url",
            "video_platform",
            "video_duration_seconds",
            "video_thumbnail",
            "audio_url",
            "audio_duration_seconds",
            "slides_url",
            "slides_count",
        ]
        widgets = {
            "video_url": forms.URLInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "https://youtube.com/...",
                }
            ),
            "video_platform": forms.Select(attrs={"class": "form-select"}),
            "video_duration_seconds": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "video_thumbnail": forms.FileInput(attrs={"class": "form-control"}),
            "audio_url": forms.URLInput(attrs={"class": "form-control"}),
            "audio_duration_seconds": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "slides_url": forms.URLInput(attrs={"class": "form-control"}),
            "slides_count": forms.NumberInput(attrs={"class": "form-control"}),
        }


class LessonResourceForm(forms.ModelForm):
    class Meta:
        model = LessonResource
        fields = ["title", "url", "resource_type", "order"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "url": forms.URLInput(attrs={"class": "form-control"}),
            "resource_type": forms.Select(attrs={"class": "form-select"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


class LessonPracticeForm(forms.ModelForm):
    class Meta:
        model = LessonPractice
        fields = ["intro", "instructions", "success_message", "data"]
        widgets = {
            "intro": forms.Textarea(attrs={"rows": 3}),
            "instructions": forms.TextInput(attrs={"class": "form-control"}),
            "success_message": forms.TextInput(attrs={"class": "form-control"}),
            "data": forms.HiddenInput(),
        }


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = [
            "question",
            "correct_answer",
            "wrong_answers",
            "theory_summary",
            "practice_prompt",
            "explanation",
            "difficulty",
            "time_limit_seconds",
            "points",
            "bonus_time_threshold",
        ]
        widgets = {
            "question": forms.TextInput(attrs={"class": "form-control"}),
            "correct_answer": forms.TextInput(attrs={"class": "form-control"}),
            "wrong_answers": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "theory_summary": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "practice_prompt": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "explanation": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "difficulty": forms.Select(attrs={"class": "form-select"}),
            "time_limit_seconds": forms.NumberInput(attrs={"class": "form-control"}),
            "points": forms.NumberInput(attrs={"class": "form-control"}),
            "bonus_time_threshold": forms.NumberInput(attrs={"class": "form-control"}),
        }


class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "bio",
            "mascot_slug",
            "theme_slug",
            "favorite_subject",
            "xp",
            "level",
            "streak",
            "weekly_goal",
            "notifications_enabled",
            "parent_email",
        ]
        widgets = {
            "display_name": forms.TextInput(attrs={"class": "form-control"}),
            "bio": forms.Textarea(attrs={"rows": 3}),
            "mascot_slug": forms.TextInput(attrs={"class": "form-control"}),
            "theme_slug": forms.TextInput(attrs={"class": "form-control"}),
            "favorite_subject": forms.Select(attrs={"class": "form-select"}),
            "xp": forms.NumberInput(attrs={"class": "form-control"}),
            "level": forms.NumberInput(attrs={"class": "form-control"}),
            "streak": forms.NumberInput(attrs={"class": "form-control"}),
            "weekly_goal": forms.NumberInput(attrs={"class": "form-control"}),
            "parent_email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class NotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = ["email_enabled", "in_app_enabled", "digest_frequency"]
