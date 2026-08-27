"""Outbound-only notification fired when a staff member finishes an
internal training course. Mirrors apps.catalog.webhooks (course-publish
webhooks) deliberately — same fail-open/never-raise discipline, same
X-Webhook-Secret header, same blank-by-default settings pair. See
config.settings.base's STAFF_TRAINING_WEBHOOK_URL/SECRET docstring.

Deliberately does NOT email anyone itself and never fires for a normal
learner's course completion — only Course.is_staff_training=True.
Not gated on is_staff (Django-admin login rights) — see
apps.catalog.views for why training access itself isn't is_staff-based
either; anyone enrolled in one of these courses is, by definition,
someone being trained, admin account or not. The receiving side (an
HR/CRM system, currently a separate app/session) decides what to do
with a completion event, e.g. feeding a promotion-readiness score.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5


def notify_staff_training_completed(enrollment):
    """Fired once, right after an Enrollment on an is_staff_training
    Course flips to COMPLETED (see
    apps.enrollment.services._mark_enrollment_completed_if_ready).
    Caller is responsible for the is_staff_training/is_staff gate —
    this function always sends if called, so it stays a pure "build
    and POST the payload" function, easy to unit test on its own."""
    url = settings.STAFF_TRAINING_WEBHOOK_URL
    secret = settings.STAFF_TRAINING_WEBHOOK_SECRET
    if not url:
        return  # destination not configured yet — nothing to send

    course = enrollment.course
    user = enrollment.user

    # Best-effort final-exam score, if this course has one. Not every
    # staff-training course requires a final assessment (some are just
    # read-through-and-done), so this is genuinely optional.
    score_percent = None
    if course.requires_final_assessment:
        from apps.assessment.models import Attempt, Quiz

        best = (
            Attempt.objects.filter(
                enrollment=enrollment, quiz__scope=Quiz.Scope.FINAL,
                quiz__course=course, passed=True,
            )
            .order_by("-score_percent")
            .first()
        )
        score_percent = best.score_percent if best else None

    payload = {
        "event": "staff_training.completed",
        "staff_email": user.email,
        "staff_first_name": user.first_name,
        "staff_last_name": user.last_name,
        "course_title": course.title,
        "course_slug": course.slug,
        "completed_at": enrollment.completed_at.isoformat() if enrollment.completed_at else None,
        # Reaching COMPLETED status is only possible after passing the
        # final assessment on a course that requires one (see
        # is_course_complete()) — there's no "failed and gave up" path
        # that fires this webhook, so `passed` is always true here. It
        # still travels explicitly (not just implied by the event
        # firing at all) since the receiving side treats it as a
        # distinct field, not an implicit constant.
        "passed": True,
        "score_percent": score_percent,
    }
    headers = {
        "X-Webhook-Secret": secret,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
        if not response.ok:
            logger.error(
                "notify_staff_training_completed got HTTP %s for %s/%s: %s",
                response.status_code, user.email, course.slug, response.text[:500],
            )
    except Exception as exc:  # noqa: BLE001 — a failed webhook must never break marking a course complete
        logger.error(
            "notify_staff_training_completed failed for %s/%s: %s", user.email, course.slug, exc
        )
