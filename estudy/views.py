from __future__ import annotations

from functools import wraps
from urllib.parse import urlparse
from django.conf import settings

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count, Prefetch, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ClassAssignmentForm,
    ClassroomForm,
    NotificationPreferenceForm,
    ProfileForm,
    ProjectSubmissionForm,
    ReplyForm,
    ThreadForm,
)
from .models import (
    AssignmentSubmission,
    ClassAssignment,
    Classroom,
    ClassroomMembership,
    CommunityReply,
    CommunityThread,
    Lesson,
    LessonProgress,
    Notification,
    NotificationPreference,
    ParentChildLink,
    Project,
    ProjectSubmission,
    Subject,
    Test,
    TestAttempt,
    UserProfile,
)
from .services.ai import generate_hint
from .services.gamification import (
    build_overall_progress,
    get_badge_summary,
    get_leaderboard_snapshot,
    get_mission_context,
    record_lesson_completion,
)
from .services.notifications import notify_feedback, send_notification

# recommendations are used inside services, not directly in views

ROLE_STUDENT = UserProfile.ROLE_STUDENT
ROLE_TEACHER = UserProfile.ROLE_PROFESSOR
ROLE_ADMIN = UserProfile.ROLE_ADMIN
ROLE_PARENT = UserProfile.ROLE_PARENT

MODULE_LESSON_ALIASES = {
    "modul-1-alfabetizare-digitala": "nivel-1-prieteni-cu-variabilele",
}


def with_progress(context: dict, user) -> dict:
    if user.is_authenticated:
        context.setdefault("global_progress", build_overall_progress(user))
    else:
        context.setdefault(
            "global_progress", {"percent": 0, "completed": 0, "total": 0}
        )
    return context


def get_profile(user: User) -> UserProfile:
    try:
        return user.userprofile
    except UserProfile.DoesNotExist as exc:
        raise Http404("Profil lipsa") from exc


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            # Ensure the user has one of the required roles
            profile = get_profile(request.user)
            if roles and profile.status not in roles:
                return HttpResponseForbidden()
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def is_admin(user: User) -> bool:
    """Predicate for @user_passes_test to check admin status.

    Returns True when the user has an associated profile with ROLE_ADMIN.
    """
    try:
        return user.userprofile.status == ROLE_ADMIN
    except UserProfile.DoesNotExist:
        return False


def _get_competitor_domains() -> set[str]:
    raw = getattr(settings, "ESTUDY_COMPETITOR_DOMAINS", None)
    if not raw:
        return set()
    try:
        # accept list/tuple/CSV string
        if isinstance(raw, (list, tuple, set)):
            items = raw
        else:
            items = [p.strip() for p in str(raw).split(",") if p.strip()]
        return set(str(d).lower().lstrip(".") for d in items)
    except Exception:
        return set()


def _is_competitor_link(url: str) -> bool:
    """Return True when the provided URL belongs to a known competitor domain.

    Domains are read from Django setting `ESTUDY_COMPETITOR_DOMAINS` and
    compared against the URL hostname suffix.
    """
    if not url:
        return False
    try:
        netloc = urlparse(url).netloc.lower()
    except Exception:
        return False
    domains = _get_competitor_domains()
    if not domains:
        return False
    return any(netloc == domain or netloc.endswith("." + domain) for domain in domains)


def _prefetched_subjects():
    return Subject.objects.prefetch_related(
        Prefetch("lessons", queryset=Lesson.objects.order_by("date", "id"))
    ).order_by("name")


def _compute_accessibility(user, subjects=None):
    if subjects is None:
        subjects = _prefetched_subjects()
    completed_ids = set(
        LessonProgress.objects.filter(user=user, completed=True).values_list(
            "lesson_id", flat=True
        )
    )
    accessible_ids = set(completed_ids)
    locked_reasons = {}

    for subject in subjects:
        lessons = list(subject.lessons.all())
        required_lesson = None
        for lesson in lessons:
            if lesson.id in completed_ids:
                required_lesson = lesson
                continue
            if required_lesson is None or required_lesson.id == lesson.id:
                accessible_ids.add(lesson.id)
                if required_lesson is None:
                    required_lesson = lesson
            else:
                locked_reasons[lesson.id] = required_lesson
    return completed_ids, accessible_ids, locked_reasons


@login_required
def dashboard_router(request):
    profile = get_profile(request.user)
    if profile.status == ROLE_ADMIN:
        return redirect("estudy:admin_dashboard")
    if profile.status == ROLE_TEACHER:
        return redirect("estudy:teacher_dashboard")
    if profile.status == ROLE_PARENT:
        return redirect("estudy:parent_dashboard")
    return redirect("estudy:student_dashboard")


@login_required
def student_dashboard(request):
    # delegate gathering of dashboard data to service
    from .services.dashboard import build_student_dashboard

    payload = build_student_dashboard(request.user)
    # fetch notifications and leaderboard that are specific to request context
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )[:5]
    leaderboard = get_leaderboard_snapshot(limit=5)
    payload.update({"notifications": notifications, "leaderboard": leaderboard})
    return render(
        request, "estudy/dashboard_student.html", with_progress(payload, request.user)
    )


@role_required(ROLE_TEACHER)
def teacher_dashboard(request):
    profile = get_profile(request.user)
    classrooms = Classroom.objects.filter(owner=request.user).annotate(
        member_count=Count("memberships")
    )
    assignments = ClassAssignment.objects.filter(
        classroom__owner=request.user
    ).select_related("classroom")[:5]
    pending_reviews = AssignmentSubmission.objects.filter(
        assignment__classroom__owner=request.user,
        status=AssignmentSubmission.STATUS_SUBMITTED,
    ).select_related("assignment", "student")
    project_reviews = ProjectSubmission.objects.select_related(
        "project", "student"
    ).order_by("-uploaded_at")[:3]

    context = {
        "profile": profile,
        "classrooms": classrooms,
        "assignments": assignments,
        "pending_reviews": pending_reviews[:5],
        "project_reviews": project_reviews,
    }
    return render(
        request, "estudy/dashboard_teacher.html", with_progress(context, request.user)
    )


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    lessons = Lesson.objects.select_related("subject").annotate(
        student_count=Count("progress_records")
    )
    top_subjects = Subject.objects.annotate(total=Count("lessons")).order_by("-total")[
        :5
    ]
    total_students = UserProfile.objects.filter(status=ROLE_STUDENT).count()
    total_teachers = UserProfile.objects.filter(status=ROLE_TEACHER).count()
    total_parents = UserProfile.objects.filter(status=ROLE_PARENT).count()
    total_classrooms = Classroom.objects.count()

    context = {
        "lessons": lessons,
        "top_subjects": top_subjects,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_parents": total_parents,
        "total_classrooms": total_classrooms,
    }
    return render(
        request, "estudy/dashboard_admin.html", with_progress(context, request.user)
    )


@role_required(ROLE_PARENT)
def parent_dashboard(request):
    links = ParentChildLink.objects.filter(parent=request.user).select_related("child")
    children = [link.child for link in links]
    child_progress = []
    for child in children:
        progress = build_overall_progress(child)
        child_progress.append(
            {
                "child": child,
                "progress": progress,
                "badges": get_badge_summary(child),
            }
        )
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )[:10]
    context = {"children": child_progress, "notifications": notifications}
    return render(
        request, "estudy/dashboard_parent.html", with_progress(context, request.user)
    )


@login_required
def lessons_list(request):
    lessons_queryset = Lesson.objects.select_related("subject").order_by("date")

    query = request.GET.get("q", "").strip()
    subject_filter = request.GET.get("subject", "").strip()
    difficulty_filter = request.GET.get("difficulty", "").strip()
    upcoming_only = request.GET.get("upcoming") == "1"

    if subject_filter:
        lessons_queryset = lessons_queryset.filter(subject_id=subject_filter)
    if difficulty_filter:
        lessons_queryset = lessons_queryset.filter(difficulty=difficulty_filter)
    if query:
        lessons_queryset = lessons_queryset.filter(
            Q(title__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(content__icontains=query)
            | Q(subject__name__icontains=query)
        )
    if upcoming_only:
        lessons_queryset = lessons_queryset.filter(date__gte=timezone.localdate())

    # delegate the heavy lifting to the lessons service
    from .services.lessons import prepare_lessons_list

    params = {
        "query": query,
        "subject": subject_filter,
        "difficulty": difficulty_filter,
        "upcoming": upcoming_only,
    }
    context = prepare_lessons_list(request.user, params)
    return render(
        request, "estudy/lessons_list.html", with_progress(context, request.user)
    )


@login_required
def missions_view(request):
    context = {
        "missions": get_mission_context(request.user),
    }
    return render(request, "estudy/missions.html", with_progress(context, request.user))


@login_required
def leaderboard_view(request):
    classroom_id = request.GET.get("classroom")
    leaderboard = get_leaderboard_snapshot(limit=20)
    classroom = None
    if classroom_id:
        classroom = get_object_or_404(Classroom, pk=classroom_id)
        member_usernames = set(
            ClassroomMembership.objects.filter(classroom=classroom).values_list(
                "user__username", flat=True
            )
        )
        leaderboard = [
            entry for entry in leaderboard if entry["username"] in member_usernames
        ]
    classrooms = ClassroomMembership.objects.filter(user=request.user).select_related(
        "classroom"
    )
    return render(
        request,
        "estudy/leaderboard.html",
        with_progress(
            {
                "leaderboard": leaderboard,
                "classrooms": classrooms,
                "selected_classroom": classroom,
            },
            request.user,
        ),
    )


@login_required
def notifications_center(request):
    notifications = Notification.objects.filter(recipient=request.user).order_by(
        "-created_at"
    )
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = NotificationPreferenceForm(request.POST, instance=prefs)
        if form.is_valid():
            form.save()
            messages.success(request, "Preferintele de notificare au fost actualizate.")
            return redirect("estudy:notifications")
    else:
        form = NotificationPreferenceForm(instance=prefs)
    return render(
        request,
        "estudy/notifications.html",
        with_progress({"notifications": notifications, "form": form}, request.user),
    )


@login_required
def classroom_hub(request):
    profile = get_profile(request.user)
    memberships = ClassroomMembership.objects.filter(user=request.user).select_related(
        "classroom"
    )
    classrooms = (
        Classroom.objects.filter(owner=request.user)
        if profile.status == ROLE_TEACHER
        else None
    )
    join_error = None
    if request.method == "POST" and profile.status == ROLE_TEACHER:
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.owner = request.user
            classroom.save()
            messages.success(request, "Clasa a fost creata cu succes.")
            return redirect("estudy:classrooms")
    elif request.method == "POST" and profile.status != ROLE_TEACHER:
        code = request.POST.get("invite_code", "").strip().upper()
        try:
            classroom = Classroom.objects.get(invite_code=code, archived=False)
            ClassroomMembership.objects.get_or_create(
                classroom=classroom, user=request.user
            )
            messages.success(request, f"Te-ai alaturat clasei {classroom.name}!")
            return redirect("estudy:classrooms")
        except Classroom.DoesNotExist:
            join_error = "Cod invalid."
        form = ClassroomForm()
    else:
        form = ClassroomForm()

    return render(
        request,
        "estudy/classrooms.html",
        with_progress(
            {
                "form": form,
                "memberships": memberships,
                "owned": classrooms,
                "join_error": join_error,
                "profile": profile,
            },
            request.user,
        ),
    )


@role_required(ROLE_TEACHER)
def classroom_detail(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk, owner=request.user)
    memberships = ClassroomMembership.objects.filter(
        classroom=classroom
    ).select_related("user")
    assignments = ClassAssignment.objects.filter(classroom=classroom).order_by(
        "-created_at"
    )
    if request.method == "POST":
        form = ClassAssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.classroom = classroom
            assignment.created_by = request.user
            assignment.save()
            messages.success(request, "Tema a fost publicata.")
            return redirect("estudy:classroom_detail", pk=classroom.pk)
    else:
        form = ClassAssignmentForm()
    return render(
        request,
        "estudy/classroom_detail.html",
        with_progress(
            {
                "classroom": classroom,
                "memberships": memberships,
                "assignments": assignments,
                "form": form,
            },
            request.user,
        ),
    )


@login_required
def projects_view(request):
    projects = Project.objects.select_related("lesson").order_by("level")
    submissions = ProjectSubmission.objects.filter(student=request.user)
    submitted_ids = list(submissions.values_list("project_id", flat=True))
    return render(
        request,
        "estudy/projects.html",
        with_progress(
            {
                "projects": projects,
                "submitted_project_ids": submitted_ids,
                "project_submissions": submissions,
            },
            request.user,
        ),
    )


@login_required
def submit_project(request, slug):
    project = get_object_or_404(Project, slug=slug)
    submission = ProjectSubmission.objects.filter(
        project=project, student=request.user
    ).first()
    if request.method == "POST":
        form = ProjectSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.project = project
            submission.student = request.user
            submission.save()
            notify_feedback(
                request.user,
                "Am primit proiectul tau! Profesorii il vor analiza in curand.",
                link_url=reverse("estudy:projects"),
            )
            messages.success(request, "Proiectul a fost trimis.")
            return redirect("estudy:projects")
    else:
        form = ProjectSubmissionForm(instance=submission)
    return render(
        request,
        "estudy/project_submit.html",
        with_progress({"project": project, "form": form}, request.user),
    )


@login_required
def community_forum(request):
    threads = CommunityThread.objects.select_related("created_by").order_by(
        "-is_pinned", "-created_at"
    )
    if request.method == "POST":
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.created_by = request.user
            thread.save()
            messages.success(request, "Ai creat un nou subiect de discutie.")
            return redirect("estudy:community")
    else:
        form = ThreadForm()
    return render(
        request,
        "estudy/community.html",
        with_progress({"threads": threads, "form": form}, request.user),
    )


@login_required
def community_thread(request, pk):
    thread = get_object_or_404(
        CommunityThread.objects.select_related("created_by"), pk=pk
    )
    replies = CommunityReply.objects.filter(thread=thread).select_related("created_by")
    if request.method == "POST":
        form = ReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.thread = thread
            reply.created_by = request.user
            reply.save()
            send_notification(
                recipient=thread.created_by,
                title="Cineva a raspuns in comunitate",
                message=f"{request.user.username} a raspuns la {thread.title}",
                category=Notification.CATEGORY_COMMUNITY,
            )
            return redirect("estudy:community_thread", pk=thread.pk)
    else:
        form = ReplyForm()
    return render(
        request,
        "estudy/community_thread.html",
        with_progress(
            {"thread": thread, "replies": replies, "form": form}, request.user
        ),
    )


@login_required
def lesson_module_digital_literacy(request):
    alias_slug = MODULE_LESSON_ALIASES.get(
        "modul-1-alfabetizare-digitala", "modul-1-alfabetizare-digitala"
    )
    try:
        return lesson_detail(request, slug=alias_slug)
    except Http404:
        context = {
            "module_name": "Modul 1 - Alfabetizare digitala",
        }
        return render(
            request,
            "estudy/lesson_module_digital_literacy.html",
            with_progress(context, request.user),
        )


@login_required
def lesson_detail(request, slug):
    try:
        from .services.lesson_detail import (
            BlockingLessonRequired,
            prepare_lesson_detail,
        )

        payload = prepare_lesson_detail(request.user, slug)
        return render(
            request, "estudy/lesson_detail.html", with_progress(payload, request.user)
        )
    except BlockingLessonRequired as exc:
        messages.info(request, f"Finalizează mai întâi lecția '{exc.blocking_title}'.")
        return redirect("estudy:lesson_detail", slug=exc.blocking_slug)
    except ValueError:
        raise Http404()


@require_POST
@login_required
def toggle_lesson_completion(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug)
    seconds_spent = request.POST.get("seconds")
    seconds_spent = (
        int(seconds_spent) if seconds_spent and seconds_spent.isdigit() else None
    )
    # delegate to service for testable, centralized behavior
    try:
        from .services.toggles import toggle_lesson_completion_service

        result = toggle_lesson_completion_service(
            request.user, lesson, seconds_spent=seconds_spent
        )
        snapshot = result["progress_snapshot"]
        return JsonResponse(
            {
                "completed": bool(result.get("completed")),
                "progress_percent": snapshot["percent"],
                "completed_count": snapshot["completed"],
                "total_lessons": snapshot["total"],
            }
        )
    except Exception:
        # fallback to legacy inline behavior if service fails for any reason
        progress, _ = LessonProgress.objects.get_or_create(
            user=request.user, lesson=lesson
        )

        if progress.completed:
            progress.completed = False
            progress.completed_at = None
            progress.save(update_fields=["completed", "completed_at", "updated_at"])
            progress_snapshot = build_overall_progress(request.user)
            return JsonResponse(
                {
                    "completed": False,
                    "progress_percent": progress_snapshot["percent"],
                    "completed_count": progress_snapshot["completed"],
                    "total_lessons": progress_snapshot["total"],
                }
            )

        progress_snapshot = record_lesson_completion(
            request.user, lesson, seconds_spent=seconds_spent
        )
        return JsonResponse(
            {
                "completed": True,
                "progress_percent": progress_snapshot["percent"],
                "completed_count": progress_snapshot["completed"],
                "total_lessons": progress_snapshot["total"],
            }
        )


@require_POST
@login_required
def submit_test_attempt(request, test_id):
    test = get_object_or_404(Test.objects.select_related("lesson"), pk=test_id)
    answer = request.POST.get("answer", "").strip()
    if not answer:
        return JsonResponse({"error": "Trebuie sa alegi un raspuns."}, status=400)

    try:
        from .services.assessment import process_test_attempt

        time_taken = int(request.POST.get("time_taken_ms", "0") or 0)
        response = process_test_attempt(request.user, test, answer, time_taken)
        return JsonResponse(response)
    except Exception:
        # fallback to inline behavior to avoid breaking the endpoint
        is_correct = answer == test.correct_answer
        time_taken = int(request.POST.get("time_taken_ms", "0") or 0)
        bonus = bool(
            is_correct
            and time_taken
            and (time_taken / 1000) <= test.bonus_time_threshold
        )
        awarded_points = test.points if is_correct else 0

        attempt, _ = TestAttempt.objects.update_or_create(
            test=test,
            user=request.user,
            defaults={
                "selected_answer": answer,
                "is_correct": is_correct,
                "time_taken_ms": time_taken,
                "awarded_points": awarded_points,
                "earned_bonus": bonus,
                "feedback": test.explanation if not is_correct else "Grozaav!",
            },
        )

        response = {
            "is_correct": is_correct,
            "correct_answer": test.correct_answer,
            "explanation": test.explanation,
            "awarded_points": attempt.awarded_points,
            "earned_bonus": bonus,
        }

        if is_correct:
            progress_snapshot = record_lesson_completion(
                request.user,
                test.lesson,
                seconds_spent=time_taken // 1000 if time_taken else None,
            )
            response.update(
                {
                    "lesson_completed": True,
                    "progress_percent": progress_snapshot["percent"],
                    "completed_count": progress_snapshot["completed"],
                    "total_lessons": progress_snapshot["total"],
                }
            )
        else:
            response["lesson_completed"] = False

        return JsonResponse(response)


@login_required
def edit_profile(request):
    profile = get_profile(request.user)
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
    if request.method == "POST":
        profile_form = ProfileForm(request.POST, instance=profile)
        prefs_form = NotificationPreferenceForm(request.POST, instance=prefs)
        if profile_form.is_valid() and prefs_form.is_valid():
            profile_form.save()
            prefs_form.save()
            messages.success(request, "Profil actualizat.")
            return redirect("inregistrare_profile")
    else:
        profile_form = ProfileForm(instance=profile)
        prefs_form = NotificationPreferenceForm(instance=prefs)
    return render(
        request,
        "accounts/edit_profile.html",
        with_progress({"form": profile_form, "prefs_form": prefs_form}, request.user),
    )


@login_required
def user_progress(request):
    dată = build_overall_progress(request.user)
    return JsonResponse({"progress_percent": dată["percent"]})


@login_required
def ai_hint(request, slug):
    lesson = get_object_or_404(Lesson, slug=slug)
    question = request.POST.get("question", "").strip()
    if not question:
        return JsonResponse(
            {"error": "Trimite o intrebare pentru a primi un indiciu."}, status=400
        )
    hint = generate_hint(request.user, question, lesson=lesson)
    return JsonResponse({"answer": hint.response})


@login_required
def study_overview(request):
    subjects = Subject.objects.prefetch_related("lessons")
    return render(
        request,
        "estudy/overview.html",
        with_progress(
            {
                "subjects": subjects,
                "progress_percent": build_overall_progress(request.user)["percent"],
            },
            request.user,
        ),
    )
