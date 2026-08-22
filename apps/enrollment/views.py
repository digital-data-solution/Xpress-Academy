from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .access import requires_active_enrollment
from .models import Enrollment
from .services import (
    get_lock_reason,
    get_next_lesson,
    get_progress_percent,
    is_module_unlocked,
    mark_lesson_complete,
)


@login_required
def dashboard(request):
    enrollments = (
        Enrollment.objects.filter(user=request.user)
        .exclude(status=Enrollment.Status.REVOKED)
        .select_related("course")
        .order_by("-last_activity_at", "-started_at")
    )
    rows = []
    for enrollment in enrollments:
        rows.append({
            "enrollment": enrollment,
            "progress_percent": get_progress_percent(enrollment),
            "next_lesson": get_next_lesson(enrollment),
        })
    return render(request, "enrollment/dashboard.html", {"rows": rows})


@requires_active_enrollment
def curriculum(request, course_slug, lesson_slug=None):
    course = request.course
    enrollment = request.enrollment

    completed_lesson_ids = set(
        enrollment.lesson_progress.filter(completed_at__isnull=False).values_list("lesson_id", flat=True)
    )

    from apps.assessment.models import Quiz  # local import: assessment depends on enrollment, not the reverse

    modules = []
    for module in course.modules.order_by("order").prefetch_related("lessons"):
        unlocked = is_module_unlocked(enrollment, module)
        modules.append({
            "module": module,
            "unlocked": unlocked,
            "lock_reason": None if unlocked else get_lock_reason(enrollment, module),
            "lessons": module.lessons.order_by("order"),
            "quiz": Quiz.objects.filter(scope=Quiz.Scope.MODULE, module=module).first(),
        })

    final_quiz = Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).first()

    return render(
        request,
        "enrollment/curriculum.html",
        {
            "course": course,
            "enrollment": enrollment,
            "modules": modules,
            "final_quiz": final_quiz,
            "completed_lesson_ids": completed_lesson_ids,
            "progress_percent": get_progress_percent(enrollment),
        },
    )


@requires_active_enrollment
def lesson_player(request, course_slug, lesson_slug):
    course = request.course
    lesson = request.lesson
    module = request.module
    enrollment = request.enrollment  # None for a preview lesson viewed while logged out

    completed = False
    if enrollment:
        completed = enrollment.lesson_progress.filter(lesson=lesson, completed_at__isnull=False).exists()

    all_lessons = list(module.lessons.order_by("order"))
    idx = next((i for i, l in enumerate(all_lessons) if l.id == lesson.id), 0)
    prev_lesson = all_lessons[idx - 1] if idx > 0 else None
    next_lesson = all_lessons[idx + 1] if idx + 1 < len(all_lessons) else None

    return render(
        request,
        "enrollment/lesson_player.html",
        {
            "course": course,
            "module": module,
            "lesson": lesson,
            "enrollment": enrollment,
            "completed": completed,
            "prev_lesson": prev_lesson,
            "next_lesson": next_lesson,
            "is_preview_view": enrollment is None,
        },
    )


@require_POST
@requires_active_enrollment
def mark_complete(request, course_slug, lesson_slug):
    enrollment = request.enrollment
    if not enrollment:
        # Defensive only — the template never renders this form for a
        # preview-without-enrollment view. There's no enrollment to
        # attach progress to.
        return HttpResponseForbidden("No active enrollment.")

    mark_lesson_complete(enrollment, request.lesson)
    return redirect("enrollment:lesson", course_slug=course_slug, lesson_slug=lesson_slug)
