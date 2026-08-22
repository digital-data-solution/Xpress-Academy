"""Celery tasks — build spec §5. Scheduled in config/celery.py's
beat_schedule. Each task is a thin wrapper: the real logic mostly
already existed (Phases 4-6 built it to run inline/on-demand before a
task queue existed); this file is what finally puts it on a clock.
"""

import logging

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.assessment.services import expire_all_stale_attempts
from apps.catalog.models import Module
from apps.enrollment.models import Enrollment
from apps.enrollment.services import get_progress_percent, is_module_unlocked
from apps.payments.services import reconcile_pending_payments, sweep_paystack_transactions

from .models import EmailLog, LiveSession
from .services import send_email

logger = logging.getLogger(__name__)


def _send_templated(*, to_email, template_key, subject, template_name, context, user=None, dedupe_key=None):
    context = {**context, "site_url": settings.SITE_URL}
    html = render_to_string(f"emails/{template_name}", context)
    return send_email(
        to_email=to_email, template_key=template_key, subject=subject, html=html, user=user, dedupe_key=dedupe_key,
    )


@shared_task
def unlock_dripped_modules():
    """Hourly. A DRIP_DAYS module that just became unlocked in roughly
    the last hour gets a "new module unlocked" email. dedupe_key makes
    the "roughly" safe — a module can only ever trigger one email per
    enrollment regardless of how many times this task's window
    happens to re-cover it."""
    sent = 0
    modules = Module.objects.filter(unlock_rule=Module.UnlockRule.DRIP_DAYS).select_related("course")
    for module in modules:
        enrollments = Enrollment.objects.filter(
            course=module.course, status=Enrollment.Status.ACTIVE
        ).select_related("user", "course")
        for enrollment in enrollments:
            available_from = enrollment.started_at + timezone.timedelta(days=module.drip_days)
            just_unlocked = timezone.now() - timezone.timedelta(hours=1) <= available_from <= timezone.now()
            if not just_unlocked or not is_module_unlocked(enrollment, module):
                continue
            _send_templated(
                to_email=enrollment.user.email, user=enrollment.user,
                template_key="module_unlocked", subject=f"New module unlocked: {module.title}",
                template_name="module_unlocked.html",
                context={
                    "first_name": enrollment.user.first_name or "there",
                    "course_title": enrollment.course.title, "module_title": module.title,
                    "course_slug": enrollment.course.slug,
                },
                dedupe_key=f"module_unlocked:{enrollment.id}:{module.id}",
            )
            sent += 1
    return sent


MAX_STALL_NUDGES = 3
STALL_THRESHOLD_DAYS = 7


@shared_task
def detect_stalled_learners():
    """Daily 09:00 WAT. Nudges an ACTIVE enrollment whose
    last_activity_at is 7+ days old — at most 3 times ever, then
    stops (checked by counting this enrollment's past nudge
    EmailLogs, not by a stored counter field)."""
    threshold = timezone.now() - timezone.timedelta(days=STALL_THRESHOLD_DAYS)
    stalled = Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE, last_activity_at__lte=threshold,
    ).select_related("user", "course")

    sent = 0
    for enrollment in stalled:
        nudge_count = EmailLog.objects.filter(
            template_key="stalled_nudge", dedupe_key__startswith=f"stalled_nudge:{enrollment.id}:",
            status=EmailLog.Status.SENT,
        ).count()
        if nudge_count >= MAX_STALL_NUDGES:
            continue
        _send_templated(
            to_email=enrollment.user.email, user=enrollment.user,
            template_key="stalled_nudge", subject=f"Pick up where you left off — {enrollment.course.title}",
            template_name="stalled_nudge.html",
            context={
                "first_name": enrollment.user.first_name or "there",
                "course_title": enrollment.course.title, "course_slug": enrollment.course.slug,
                "progress_percent": get_progress_percent(enrollment),
            },
            dedupe_key=f"stalled_nudge:{enrollment.id}:{nudge_count + 1}",
        )
        sent += 1
    return sent


EXPIRY_WARNING_WINDOWS_DAYS = (14, 3)


@shared_task
def warn_expiring_access():
    """Daily. Warns a TIMED enrollment 14 and 3 days before expires_at
    — two separate, independent warnings.

    Windows are treated as exclusive bands, not two independent
    "days_left <= window" checks: 14 fires for days_left in (3, 14],
    3 fires for days_left in (-inf, 3]. Checking them independently
    (an earlier version of this task did) means a days_left value like
    2 satisfies *both* conditions simultaneously, so if the 14-day
    email had somehow not gone out yet (task was down, or an
    enrollment's window is discovered late), the very next run sends
    the 14-day AND 3-day emails back to back — two near-identical
    warnings within seconds. Exclusive bands mean at most one window
    ever matches a given days_left, so at most one email goes out per
    enrollment per run, and each window still gets its own dedupe_key
    so it independently fires exactly once over the enrollment's
    lifetime, on whichever run first finds it in-band."""
    sent = 0
    candidates = Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE, expires_at__isnull=False,
    ).select_related("user", "course")

    windows_desc = sorted(EXPIRY_WARNING_WINDOWS_DAYS, reverse=True)

    for enrollment in candidates:
        days_left = (enrollment.expires_at - timezone.now()).days
        for i, window in enumerate(windows_desc):
            lower_exclusive_bound = windows_desc[i + 1] if i + 1 < len(windows_desc) else None
            in_band = days_left <= window and (lower_exclusive_bound is None or days_left > lower_exclusive_bound)
            if not in_band:
                continue
            dedupe_key = f"expiring_access:{enrollment.id}:{window}"
            if EmailLog.objects.filter(dedupe_key=dedupe_key, status=EmailLog.Status.SENT).exists():
                break  # this enrollment's current band is already handled — nothing else to check
            _send_templated(
                to_email=enrollment.user.email, user=enrollment.user,
                template_key="expiring_access", subject=f"Your access to {enrollment.course.title} is ending soon",
                template_name="expiring_access.html",
                context={
                    "first_name": enrollment.user.first_name or "there",
                    "course_title": enrollment.course.title, "course_slug": enrollment.course.slug,
                    "expires_at": enrollment.expires_at, "days_left": max(days_left, 0),
                },
                dedupe_key=dedupe_key,
            )
            sent += 1
            break  # only the tightest matching window fires per run
    return sent


@shared_task
def expire_enrollments():
    """Daily. Flips ACTIVE enrollments past expires_at to EXPIRED."""
    return Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE, expires_at__isnull=False, expires_at__lte=timezone.now(),
    ).update(status=Enrollment.Status.EXPIRED)


LIVE_SESSION_REMINDER_WINDOWS = {"24h": timezone.timedelta(hours=24), "1h": timezone.timedelta(hours=1)}


@shared_task
def remind_live_session():
    """Hourly. 24h and 1h before a LiveSession, emails every ACTIVE
    enrollee of that session's course."""
    sent = 0
    now = timezone.now()
    upcoming = LiveSession.objects.filter(is_cancelled=False, starts_at__gte=now).select_related("course")

    for session in upcoming:
        time_until = session.starts_at - now
        for window_name, window_delta in LIVE_SESSION_REMINDER_WINDOWS.items():
            # Fires once time_until drops to/under the window, same
            # "tightest matching window" idea as warn_expiring_access.
            if time_until > window_delta:
                continue
            enrollments = Enrollment.objects.filter(
                course=session.course, status=Enrollment.Status.ACTIVE
            ).select_related("user")
            for enrollment in enrollments:
                dedupe_key = f"live_session_reminder:{session.id}:{window_name}:{enrollment.id}"
                if EmailLog.objects.filter(dedupe_key=dedupe_key, status=EmailLog.Status.SENT).exists():
                    continue
                when_text = "tomorrow" if window_name == "24h" else "in about an hour"
                _send_templated(
                    to_email=enrollment.user.email, user=enrollment.user,
                    template_key="live_session_reminder", subject=f"Reminder: {session.title} {when_text}",
                    template_name="live_session_reminder.html",
                    context={
                        "first_name": enrollment.user.first_name or "there",
                        "session_title": session.title, "course_title": session.course.title,
                        "starts_at": session.starts_at, "join_url": session.join_url, "when_text": when_text,
                    },
                    dedupe_key=dedupe_key,
                )
                sent += 1
            break  # only the tightest matching window fires per session per run
    return sent


@shared_task
def expire_stale_attempts():
    """Every 15 minutes — the proactive counterpart to
    apps.assessment.services.expire_attempt_if_stale (which only
    catches an attempt reactively, when its owner revisits it)."""
    return expire_all_stale_attempts()


@shared_task
def reconcile_pending_payments_task():
    """Every 10 minutes — puts apps.payments.services.reconcile_pending_payments
    (built in Phase 6, previously only reachable via management
    command) on the schedule the payments addendum calls for."""
    return reconcile_pending_payments()


@shared_task
def sweep_paystack_transactions_task():
    """Daily 02:00 WAT — same as above for sweep_paystack_transactions."""
    return sweep_paystack_transactions()
