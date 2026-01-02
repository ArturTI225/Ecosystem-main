from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .models import LessonComment, LessonRating
from .services.notifications import (
    notify_comment_reply,
    notify_new_comment,
    notify_new_rating,
)


@receiver(post_save, sender=LessonComment)
def notify_on_new_comment(sender, instance, created, **kwargs):
    """Send notifications when new comments are created"""
    if created and instance.is_approved and instance.lesson.slug:
        lesson_url = reverse(
            "estudy:lesson_detail", kwargs={"slug": instance.lesson.slug}
        )

        # Notify teachers about new comment
        notify_new_comment(instance.user, instance.lesson.title, lesson_url)

        # Notify parent comment author about replies
        if instance.parent:
            notify_comment_reply(
                instance.parent.user, instance.user, instance.lesson.title, lesson_url
            )


@receiver(post_save, sender=LessonRating)
def notify_on_new_rating(sender, instance, created, **kwargs):
    """Send notifications when new ratings are created"""
    if created and instance.lesson.slug:
        lesson_url = reverse(
            "estudy:lesson_detail", kwargs={"slug": instance.lesson.slug}
        )
        notify_new_rating(
            instance.user, instance.lesson.title, instance.rating, lesson_url
        )
