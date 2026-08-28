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
    """Designed to run hourly (see config/celery.py's beat_schedule),
    but in production today only actually runs once a day, via the
    free-tier run_scheduled_tasks cron (see the Render deploy notes —
    no real worker/beat yet). Previously only sent when a module's
    unlock moment fell inside a ±1-hour window around whenever this
    happened to run — which meant most drip unlocks silently got no
    email at all under a once-daily cron, since the window rarely
    lines up. Fixed: no time window at all now — just "is this module
    unlocked right now, for this active enrollment" — dedupe_key alone
    (not a time window) is what prevents a resend, so this is correct
    and safe whether it's called hourly or once a day.

    Also pings ops (see apps.operations.services._ops_recipient, same
    address as every other ops-facing notification) when the unlocked
    module belongs to an is_compulsory_staff_training course — the
    "remind me as admin too" half of the compulsory staff-training
    track, so a real person notices alongside the automated email."""
    sent = 0
    modules = Module.objects.filter(unlock_rule=Module.UnlockRule.DRIP_DAYS).select_related("course")
    for module in modules:
        enrollments = Enrollment.objects.filter(
            course=module.course, status=Enrollment.Status.ACTIVE
        ).select_related("user", "course")
        for enrollment in enrollments:
            if not is_module_unlocked(enrollment, module):
                continue

            # Check dedupe existence ourselves, rather than counting
            # every call to _send_templated as "sent" — send_email()'s
            # own dedupe silently returns the existing (already-SENT)
            # log instead of sending again, which would otherwise make
            # this function's return value count re-runs as new sends
            # too.
            learner_key = f"module_unlocked:{enrollment.id}:{module.id}"
            if not EmailLog.objects.filter(dedupe_key=learner_key).exists():
                _send_templated(
                    to_email=enrollment.user.email, user=enrollment.user,
                    template_key="module_unlocked", subject=f"New module unlocked: {module.title}",
                    template_name="module_unlocked.html",
                    context={
                        "first_name": enrollment.user.first_name or "there",
                        "course_title": enrollment.course.title, "module_title": module.title,
                        "course_slug": enrollment.course.slug,
                    },
                    dedupe_key=learner_key,
                )
                sent += 1

            if module.course.is_compulsory_staff_training:
                ops_key = f"compulsory_training_unlocked:{enrollment.id}:{module.id}"
                if not EmailLog.objects.filter(dedupe_key=ops_key).exists():
                    from apps.operations.services import _ops_recipient

                    ops_email = _ops_recipient(enrollment.course.organization)
                    if ops_email:
                        _send_templated(
                            to_email=ops_email, template_key="compulsory_training_unlocked",
                            subject=f"Reminder: {enrollment.user.email}'s next training module is ready",
                            template_name="compulsory_training_unlocked.html",
                            context={
                                "staff_email": enrollment.user.email,
                                "course_title": enrollment.course.title, "module_title": module.title,
                            },
                            dedupe_key=ops_key,
                        )
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


@shared_task
def send_graduate_marketing_emails_task():
    """Daily — introduces newly-certified, marketing-opted-in graduates
    to Xpress Vet Marketplace. See apps.certificates.marketing's
    module docstring for the consent gate and no-retroactive-blast
    scoping; the actual logic lives there since it's fundamentally
    about certificates, not engagement mechanics — this is a thin
    wrapper only, same as reconcile_pending_payments_task above."""
    from apps.certificates.marketing import send_graduate_marketing_emails
    return send_graduate_marketing_emails()


@shared_task
def send_weekly_staff_training_email_task():
    """Runs daily via run_scheduled_tasks (no real weekly cron slot on
    the free tier — see the Render deploy notes), but only actually
    sends on Mondays; every other day is a no-op, same "call it daily,
    let it self-gate" shape as nothing else here needed until now.

    Deliberately NOT is_staff-based (see apps.catalog.views for the
    matching access-control note) — someone can be assigned training
    with a plain, non-admin Academy account. Whoever is being trained
    is defined entirely by Enrollment: an admin enrolls a user in an
    is_staff_training Course (Enrollment admin, same as any course),
    and this task emails everyone with at least one such enrollment
    the specific course(s) *they're* enrolled in, not a global menu —
    they can't view a course here they aren't enrolled in. dedupe_key
    is scoped per-user per-ISO-week, so re-running this same Monday (a
    retried GitHub Actions run, a redeploy) never double-sends."""
    if timezone.localtime().weekday() != 0:  # Monday only
        return "skipped (not Monday)"

    from apps.accounts.models import User
    from apps.catalog.models import Course
    from apps.enrollment.models import Enrollment

    recipient_ids = (
        Enrollment.objects.filter(course__is_staff_training=True, course__is_published=True, user__is_active=True)
        .values_list("user_id", flat=True).distinct()
    )
    if not recipient_ids:
        return "skipped (no staff-training enrollments)"

    monday = timezone.localdate()
    sent = 0
    for user in User.objects.filter(id__in=recipient_ids):
        courses = Course.objects.filter(
            is_staff_training=True, is_published=True, enrollments__user=user,
        ).distinct().order_by("title")
        _send_templated(
            to_email=user.email, template_key="staff_training_weekly",
            subject="This week's staff training", template_name="staff_training_weekly.html",
            context={"first_name": user.first_name or "there", "courses": courses},
            user=user, dedupe_key=f"staff-training-weekly:{user.id}:{monday.isoformat()}",
        )
        sent += 1
    return f"sent {sent}"


@shared_task
def advance_compulsory_training_chains_task():
    """Runs daily via run_scheduled_tasks. Course-to-course pacing for
    a compulsory training sequence (e.g. the 15-course general
    onboarding track) — separate from unlock_dripped_modules, which
    paces content WITHIN one course. A course only enrolls here if it
    has both is_compulsory_staff_training=True and a prerequisite set
    (a chain head with no prerequisite is enrolled immediately on
    group-join instead — see apps.accounts.signal_receivers).

    For each such course: find every user who COMPLETED its
    prerequisite at least unlock_delay_days ago and isn't already
    enrolled in this course, enroll them, email them, and ping ops —
    same "remind me as admin too" pattern as unlock_dripped_modules'
    compulsory-course echo. get_or_create on the Enrollment plus a
    dedupe_key'd email means running this daily is safe — a user
    already enrolled/already emailed is a no-op."""
    from apps.catalog.models import Course
    from apps.enrollment.models import Enrollment
    from apps.operations.services import _ops_recipient

    sent = 0
    chained_courses = Course.objects.filter(
        is_staff_training=True, is_compulsory_staff_training=True, is_published=True, prerequisite__isnull=False,
    ).select_related("prerequisite", "organization")

    for course in chained_courses:
        cutoff = timezone.now() - timezone.timedelta(days=course.unlock_delay_days)
        eligible = Enrollment.objects.filter(
            course=course.prerequisite, status=Enrollment.Status.COMPLETED, completed_at__lte=cutoff,
        ).exclude(
            user__enrollments__course=course,
        ).select_related("user")

        for prior_enrollment in eligible:
            user = prior_enrollment.user
            Enrollment.objects.get_or_create(user=user, course=course)
            dedupe_key = f"chain_unlocked:{user.id}:{course.id}"
            if not EmailLog.objects.filter(dedupe_key=dedupe_key).exists():
                _send_templated(
                    to_email=user.email, user=user,
                    template_key="chain_course_unlocked", subject=f"Your next course is ready: {course.title}",
                    template_name="chain_course_unlocked.html",
                    context={
                        "first_name": user.first_name or "there",
                        "course_title": course.title, "course_slug": course.slug,
                    },
                    dedupe_key=dedupe_key,
                )
                sent += 1

                ops_key = f"chain_unlocked_ops:{user.id}:{course.id}"
                if not EmailLog.objects.filter(dedupe_key=ops_key).exists():
                    ops_email = _ops_recipient(course.organization)
                    if ops_email:
                        _send_templated(
                            to_email=ops_email, template_key="chain_course_unlocked_ops",
                            subject=f"Reminder: {user.email}'s next training course is ready",
                            template_name="chain_course_unlocked_ops.html",
                            context={"staff_email": user.email, "course_title": course.title},
                            dedupe_key=ops_key,
                        )
    return f"sent {sent}"
