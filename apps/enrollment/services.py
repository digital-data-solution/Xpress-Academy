"""Business logic for enrollment and progress. Views must call these
functions rather than re-deriving unlock/completion logic themselves —
see build spec §4: "Module unlock is computed, not stored. One
service function ... evaluates the rule chain. Every view and template
calls that one function. Do not scatter the logic."
"""

from django.utils import timezone

from apps.catalog.models import Module

from .models import Enrollment, LessonProgress


def is_enrollment_currently_active(enrollment: Enrollment) -> bool:
    """Real-time access check. status == ACTIVE alone isn't enough —
    an enrollment can be logically expired before the (Phase 7)
    `expire_enrollments` Celery task has run and flipped the status
    field, so expires_at is always checked live here too."""
    if enrollment.status != Enrollment.Status.ACTIVE:
        return False
    if enrollment.expires_at and enrollment.expires_at <= timezone.now():
        return False
    return True


def is_module_completed(enrollment: Enrollment, module: Module) -> bool:
    """A module is complete when every one of its lessons has a
    LessonProgress with completed_at set for this enrollment, AND —
    when the module requires it — there's a passing Attempt on its
    module quiz. Phase 4 extension point, filled in as promised in
    the Phase 3 docstring here rather than scattered into callers.
    """
    lesson_ids = list(module.lessons.values_list("id", flat=True))
    if not lesson_ids:
        return False
    completed_count = LessonProgress.objects.filter(
        enrollment=enrollment,
        lesson_id__in=lesson_ids,
        completed_at__isnull=False,
    ).count()
    if completed_count != len(lesson_ids):
        return False

    if module.requires_quiz_pass_to_advance:
        from apps.assessment.models import Attempt, Quiz

        quiz = Quiz.objects.filter(scope=Quiz.Scope.MODULE, module=module).first()
        if quiz is None:
            # Flag set but no quiz authored yet — fail closed, not open.
            return False
        return Attempt.objects.filter(enrollment=enrollment, quiz=quiz, passed=True).exists()

    return True


def is_course_complete(enrollment: Enrollment) -> bool:
    """Every lesson in every module complete, AND — when the course
    requires it — a passing Attempt on its FINAL quiz. Phase 4/5
    extension point promised in the old mark_lesson_complete
    docstring; centralised here instead of inlined so certificates
    (Phase 5) can call the same function completion relies on."""
    all_lessons = [l for m in enrollment.course.modules.all() for l in m.lessons.all()]
    if not all_lessons:
        return False
    all_done = all(
        LessonProgress.objects.filter(
            enrollment=enrollment, lesson=l, completed_at__isnull=False
        ).exists()
        for l in all_lessons
    )
    if not all_done:
        return False

    if enrollment.course.requires_final_assessment:
        from apps.assessment.models import Attempt, Quiz

        quiz = Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=enrollment.course).first()
        if quiz is None:
            return False
        return Attempt.objects.filter(enrollment=enrollment, quiz=quiz, passed=True).exists()

    return True


def is_module_unlocked(enrollment: Enrollment, module: Module) -> bool:
    """The single source of truth for module access. Every view and
    template must call this rather than re-deriving the rule chain."""
    course = module.course

    if module.unlock_rule == Module.UnlockRule.IMMEDIATE:
        return True

    if module.unlock_rule == Module.UnlockRule.DRIP_DAYS:
        available_from = enrollment.started_at + timezone.timedelta(days=module.drip_days)
        return timezone.now() >= available_from

    # SEQUENTIAL: unlocked if it's the first module in the course, or
    # the previous module (by order) is complete.
    modules = list(course.modules.order_by("order").only("id", "order"))
    index = next((i for i, m in enumerate(modules) if m.id == module.id), None)
    if index is None or index == 0:
        return True
    previous_module = modules[index - 1]
    # Re-fetch with lessons prefetched would be an optimisation; correctness first.
    previous_module = Module.objects.get(pk=previous_module.id)
    return is_module_completed(enrollment, previous_module)


def get_lock_reason(enrollment: Enrollment, module: Module) -> str | None:
    """Human-readable reason a module is locked, for display in the
    curriculum view. Returns None if the module is unlocked."""
    if is_module_unlocked(enrollment, module):
        return None

    if module.unlock_rule == Module.UnlockRule.DRIP_DAYS:
        available_from = enrollment.started_at + timezone.timedelta(days=module.drip_days)
        days_left = (available_from - timezone.now()).days + 1
        return f"Unlocks in {max(days_left, 1)} day{'s' if days_left != 1 else ''}"

    return "Complete the previous module first"


def get_next_lesson(enrollment: Enrollment):
    """First lesson, in course order, that is in an unlocked module
    and doesn't yet have a completed LessonProgress. None if every
    unlocked lesson is done (course complete or waiting on a lock)."""
    for module in enrollment.course.modules.order_by("order"):
        if not is_module_unlocked(enrollment, module):
            break
        for lesson in module.lessons.order_by("order"):
            done = LessonProgress.objects.filter(
                enrollment=enrollment, lesson=lesson, completed_at__isnull=False
            ).exists()
            if not done:
                return lesson
    return None


def get_progress_percent(enrollment: Enrollment) -> int:
    total = sum(m.lessons.count() for m in enrollment.course.modules.all())
    if total == 0:
        return 0
    done = LessonProgress.objects.filter(
        enrollment=enrollment, completed_at__isnull=False
    ).count()
    return round(done * 100 / total)


def _mark_enrollment_completed_if_ready(enrollment: Enrollment) -> None:
    if enrollment.status == Enrollment.Status.ACTIVE and is_course_complete(enrollment):
        enrollment.status = Enrollment.Status.COMPLETED
        enrollment.completed_at = timezone.now()
        enrollment.save(update_fields=["status", "completed_at", "updated_at"])

        # Local import: apps.certificates.services imports
        # is_course_complete from this module, so a module-level
        # import here would be circular.
        from apps.certificates.services import issue_certificate

        issue_certificate(enrollment)


def mark_lesson_complete(enrollment: Enrollment, lesson) -> LessonProgress:
    """Idempotent. Bumps last_activity_at, and marks the enrollment
    COMPLETED if this was the piece that made is_course_complete()
    true (a course with no final assessment completes on its last
    lesson; one that requires it still needs a passing final Attempt
    too — see finalize_attempt in apps.assessment.services, which
    calls _mark_enrollment_completed_if_ready the same way after a
    quiz pass)."""
    progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    if not progress.completed_at:
        progress.completed_at = timezone.now()
        progress.save(update_fields=["completed_at", "updated_at"])

    enrollment.last_activity_at = timezone.now()
    enrollment.save(update_fields=["last_activity_at", "updated_at"])

    _mark_enrollment_completed_if_ready(enrollment)
    return progress
