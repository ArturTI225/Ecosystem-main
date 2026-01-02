from django.contrib import admin

from .models import CodeExercise, Lesson, Subject, Test


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "date",
        "difficulty",
        "age_bracket",
        "duration_minutes",
    )
    list_filter = ("subject", "difficulty", "age_bracket", "date")
    search_fields = ("title", "subject__name", "content")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(CodeExercise)
class CodeExerciseAdmin(admin.ModelAdmin):
    list_display = ("title", "lesson", "language", "difficulty_level", "points")
    list_filter = ("language", "difficulty_level")
    search_fields = ("title", "lesson__title")


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("question", "lesson", "difficulty", "points")
    list_filter = ("difficulty",)
    search_fields = ("question", "lesson__title")
