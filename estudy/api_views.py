from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CommentLike,
    Lesson,
    LessonAnalytics,
    LessonComment,
    LessonProgress,
    LessonRating,
)
from .serializers import (
    LessonAnalyticsSerializer,
    LessonCommentSerializer,
    LessonProgressSerializer,
    LessonRatingSerializer,
)


class LessonCommentsListCreateView(generics.ListCreateAPIView):
    """API view for listing and creating lesson comments"""

    serializer_class = LessonCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lesson_slug = self.kwargs.get("lesson_slug")
        lesson = get_object_or_404(Lesson, slug=lesson_slug)

        # Get top-level comments (no parent)
        queryset = (
            LessonComment.objects.filter(
                lesson=lesson, parent__isnull=True, is_approved=True, is_hidden=False
            )
            .select_related("user")
            .prefetch_related("likes", "replies")
        )

        # Annotate with likes and replies count
        queryset = queryset.annotate(
            likes_count=Count("likes"), replies_count=Count("replies")
        ).order_by("-created_at")

        return queryset

    def perform_create(self, serializer):
        lesson_slug = self.kwargs.get("lesson_slug")
        lesson = get_object_or_404(Lesson, slug=lesson_slug)
        serializer.save(lesson=lesson, user=self.request.user)


class LessonCommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting lesson comments"""

    serializer_class = LessonCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LessonComment.objects.filter(user=self.request.user)


class CommentRepliesView(generics.ListCreateAPIView):
    """API view for comment replies"""

    serializer_class = LessonCommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        comment_id = self.kwargs.get("comment_id")
        return (
            LessonComment.objects.filter(
                parent_id=comment_id, is_approved=True, is_hidden=False
            )
            .select_related("user")
            .prefetch_related("likes")
            .order_by("created_at")
        )

    def perform_create(self, serializer):
        comment_id = self.kwargs.get("comment_id")
        parent_comment = get_object_or_404(LessonComment, id=comment_id)
        serializer.save(
            lesson=parent_comment.lesson, parent=parent_comment, user=self.request.user
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_comment_like(request, comment_id):
    """Toggle like on a comment"""
    comment = get_object_or_404(LessonComment, id=comment_id)
    like, created = CommentLike.objects.get_or_create(
        comment=comment, user=request.user
    )

    if not created:
        like.delete()
        return Response({"liked": False, "likes_count": comment.likes.count()})

    return Response({"liked": True, "likes_count": comment.likes.count()})


class LessonRatingCreateView(generics.CreateAPIView):
    """API view for creating lesson ratings"""

    serializer_class = LessonRatingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        lesson_slug = self.kwargs.get("lesson_slug")
        lesson = get_object_or_404(Lesson, slug=lesson_slug)
        serializer.save(lesson=lesson, user=self.request.user)


class LessonRatingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting lesson ratings"""

    serializer_class = LessonRatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LessonRating.objects.filter(user=self.request.user)


class LessonAnalyticsView(generics.ListAPIView):
    """API view for lesson analytics (teacher only)"""

    serializer_class = LessonAnalyticsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only teachers and admins can access analytics
        if not (
            self.request.user.userprofile.is_teacher()
            or self.request.user.userprofile.is_admin()
        ):
            return LessonAnalytics.objects.none()

        lesson_slug = self.kwargs.get("lesson_slug")
        if lesson_slug:
            lesson = get_object_or_404(Lesson, slug=lesson_slug)
            return LessonAnalytics.objects.filter(lesson=lesson).order_by("-date")

        # Return analytics for all lessons if no specific lesson
        return LessonAnalytics.objects.all().order_by("-date")[:100]


class LessonProgressListView(generics.ListAPIView):
    """API view for user's lesson progress"""

    serializer_class = LessonProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            LessonProgress.objects.filter(user=self.request.user)
            .select_related("lesson")
            .order_by("-updated_at")
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def lesson_stats(request, lesson_slug):
    """Get comprehensive lesson statistics"""
    lesson = get_object_or_404(Lesson, slug=lesson_slug)

    # Basic stats
    total_views = LessonProgress.objects.filter(lesson=lesson).count()
    completions = LessonProgress.objects.filter(lesson=lesson, completed=True).count()
    completion_rate = (completions / total_views * 100) if total_views > 0 else 0

    # Ratings stats
    ratings = LessonRating.objects.filter(lesson=lesson)
    avg_rating = ratings.aggregate(Avg("rating"))["rating__avg"] or 0
    ratings_count = ratings.count()

    # Comments stats
    comments_count = LessonComment.objects.filter(
        lesson=lesson, is_approved=True, is_hidden=False
    ).count()

    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_completions = LessonProgress.objects.filter(
        lesson=lesson, completed_at__gte=thirty_days_ago
    ).count()

    return Response(
        {
            "lesson": lesson.title,
            "total_views": total_views,
            "completions": completions,
            "completion_rate": round(completion_rate, 1),
            "avg_rating": round(avg_rating, 1),
            "ratings_count": ratings_count,
            "comments_count": comments_count,
            "recent_completions": recent_completions,
        }
    )
