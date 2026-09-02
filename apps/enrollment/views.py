import hmac
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .access import requires_active_enrollment
from .models import Enrollment
from .services import (
    all_lessons_completed,
    get_lock_reason,
    get_next_lesson,
    get_progress_percent,
    is_module_unlocked,
    mark_lesson_complete,
)

logger = logging.getLogger(__name__)


@login_required
def dashboard(request):
    enrollments = (
        Enrollment.objects.filter(user=request.user)
        .exclude(status=Enrollment.Status.REVOKED)
        .select_related("course")
        .order_by("-last_activity_at", "-started_at")
    )
    rows = []
    completed_count = 0
    certificate_count = 0
    for enrollment in enrollments:
        certificate = getattr(enrollment, "certificate", None)
        if enrollment.status == Enrollment.Status.COMPLETED:
            completed_count += 1
        if certificate:
            certificate_count += 1
        rows.append({
            "enrollment": enrollment,
            "progress_percent": get_progress_percent(enrollment),
            "next_lesson": get_next_lesson(enrollment),
            "certificate": certificate,
        })
    return render(request, "enrollment/dashboard.html", {
        "rows": rows,
        "completed_count": completed_count,
        "certificate_count": certificate_count,
        "in_progress_count": len(rows) - completed_count,
    })


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
            # Gates whether the final exam is shown as a live link vs a
            # locked notice — the actual enforcement is server-side in
            # apps.assessment.access.requires_quiz_access, this is just
            # so the page doesn't show a link that would only redirect
            # you straight back here.
            "final_quiz_unlocked": all_lessons_completed(enrollment),
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

    # Spans the WHOLE course, not just this lesson's module — a
    # module with only one lesson (common; every module in the demo
    # course has exactly one) previously had no "next" at all once
    # you finished it, a real dead end rather than a design choice.
    all_lessons = []
    for m in course.modules.order_by("order"):
        all_lessons.extend(m.lessons.order_by("order"))
    idx = next((i for i, l in enumerate(all_lessons) if l.id == lesson.id), 0)
    prev_lesson = all_lessons[idx - 1] if idx > 0 else None
    next_lesson = all_lessons[idx + 1] if idx + 1 < len(all_lessons) else None

    # If this is the last lesson in its module, surface that module's
    # quiz (if any) as an explicit next step too — otherwise it's only
    # ever reachable by going back to the curriculum page.
    module_quiz = None
    final_quiz = None
    if lesson.id == list(module.lessons.order_by("order"))[-1].id:
        from apps.assessment.models import Quiz
        module_quiz = Quiz.objects.filter(scope=Quiz.Scope.MODULE, module=module).first()
        # This is also the last lesson of the LAST module — surface
        # the final exam directly too, so finishing the course doesn't
        # require going back to the curriculum page just to find it.
        if not next_lesson:
            final_quiz = Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).first()

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
            "module_quiz": module_quiz,
            "final_quiz": final_quiz,
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


CALL_CANDIDATES_MAX_LIMIT = 500
CALL_CANDIDATES_DEFAULT_LIMIT = 100


@csrf_exempt
@require_GET
def call_candidates(request):
    """Read-only, inbound, shared-secret-gated endpoint for the Xpress
    Digital & Data Solutions "Call Assignment" system (built there, not
    here) to pull real Academy learner/enrollment segments instead of
    Sam pasting names in by hand — his own explicit ask, relayed then
    confirmed directly with him before building. Same shared-secret
    pattern as apps.engagement.views.run_scheduled_tasks, just GET
    instead of POST since this only ever reads.

    Deliberately conservative: GET only, no mutation; requires the
    secret even to reveal that it's configured (blank config = 403,
    same as CRON_SECRET); results capped at CALL_CANDIDATES_MAX_LIMIT
    per call rather than allowing a single request to dump the entire
    enrollment table; every access is logged (who/what filters/how
    many rows) since this returns real contact info (name/email/phone)
    -- deliberately NOT redacted the way apps.instructors' learner-
    privacy rule redacts contact info from instructors, because the
    caller here is Sam's own internal ops tool, same trust level as
    Sam's own admin access, not an external instructor.

    Query params (all optional):
      course_slug     -- exact match on Course.slug
      programme_slug  -- exact match on Course.programme.slug
      status          -- comma-separated Enrollment.Status values
                         (default: ACTIVE only, the most useful default
                         for "who should we call" -- pass status=ALL
                         for every status including REVOKED)
      limit            -- default 100, capped at 500
    """
    token = request.headers.get("X-Call-Assignment-Secret", "")
    if not settings.CALL_ASSIGNMENT_API_SECRET or not hmac.compare_digest(
        token, settings.CALL_ASSIGNMENT_API_SECRET
    ):
        return HttpResponseForbidden("Forbidden")

    qs = Enrollment.objects.select_related(
        "user", "user__profile", "course", "course__programme"
    ).order_by("-started_at")

    course_slug = request.GET.get("course_slug", "").strip()
    if course_slug:
        qs = qs.filter(course__slug=course_slug)

    programme_slug = request.GET.get("programme_slug", "").strip()
    if programme_slug:
        qs = qs.filter(course__programme__slug=programme_slug)

    status_param = request.GET.get("status", "").strip()
    if status_param and status_param.upper() != "ALL":
        statuses = [s.strip().upper() for s in status_param.split(",") if s.strip()]
        valid_statuses = {choice for choice, _ in Enrollment.Status.choices}
        statuses = [s for s in statuses if s in valid_statuses]
        if statuses:
            qs = qs.filter(status__in=statuses)
    elif not status_param:
        qs = qs.filter(status=Enrollment.Status.ACTIVE)
    # status=ALL (any case) -- no status filter, every status included.

    try:
        limit = int(request.GET.get("limit", CALL_CANDIDATES_DEFAULT_LIMIT))
    except ValueError:
        limit = CALL_CANDIDATES_DEFAULT_LIMIT
    limit = max(1, min(limit, CALL_CANDIDATES_MAX_LIMIT))

    total_matching = qs.count()
    rows = []
    for enrollment in qs[:limit]:
        user = enrollment.user
        profile = getattr(user, "profile", None)
        rows.append({
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": profile.phone if profile else "",
            "whatsapp_number": profile.whatsapp_number if profile else "",
            "course_title": enrollment.course.title,
            "course_slug": enrollment.course.slug,
            "programme": enrollment.course.programme.title if enrollment.course.programme_id else None,
            "enrollment_status": enrollment.status,
            "started_at": enrollment.started_at.isoformat() if enrollment.started_at else None,
            "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None,
            "last_activity_at": enrollment.last_activity_at.isoformat() if enrollment.last_activity_at else None,
        })

    logger.info(
        "call_candidates accessed: course_slug=%r programme_slug=%r status=%r limit=%s "
        "matched=%s returned=%s",
        course_slug, programme_slug, status_param, limit, total_matching, len(rows),
    )

    return JsonResponse({
        "count": len(rows),
        "total_matching": total_matching,
        "results": rows,
    })
