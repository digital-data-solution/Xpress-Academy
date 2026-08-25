"""The daily digest — build spec §3.1. One email, 07:00 WAT, structured
exactly as specified: Decide today / This week / Watch / Numbers / Quiet.
The "Nothing needs a decision today" line is what earns the digest its
credibility — never let this render as busy when it isn't.
"""

from django.template.loader import render_to_string
from django.utils import timezone

from apps.enrollment.models import Enrollment
from apps.payments.models import Payment

from .models import CalendarObligation, DigestRun, Signal
from .services import _ops_recipient, get_recent_dismissal_streak


def build_digest_context(organization) -> dict:
    open_signals = Signal.objects.filter(organization=organization).exclude(
        status__in=[Signal.Status.RESOLVED, Signal.Status.DISMISSED, Signal.Status.SNOOZED]
    )

    decide_today = list(
        open_signals.filter(severity__in=[Signal.Severity.URGENT, Signal.Severity.CRITICAL]).order_by("-severity")
    )
    watch = list(open_signals.filter(severity=Signal.Severity.ATTENTION))
    quiet_count = open_signals.filter(severity=Signal.Severity.INFO).count()

    week_end = timezone.now().date() + timezone.timedelta(days=7)
    obligations_this_week = CalendarObligation.objects.filter(
        organization=organization, status=CalendarObligation.Status.PENDING,
        due_date__lte=week_end,
    ).order_by("due_date")
    decisions_due_this_week = open_signals.filter(
        decision_due__isnull=False, decision_due__lte=week_end
    ).exclude(id__in=[s.id for s in decide_today])

    yesterday = timezone.now() - timezone.timedelta(days=1)
    revenue_kobo = sum(
        Payment.objects.filter(status=Payment.Status.SUCCESS, paid_at__gte=yesterday).values_list(
            "amount_kobo", flat=True
        )
    )
    numbers = {
        "new_enrollments": Enrollment.objects.filter(started_at__gte=yesterday).count(),
        # Stored in kobo everywhere else in this codebase (Payment
        # .amount_kobo) — this is the one place that turns it into the
        # ₦ figure a person actually reads, so it's computed once here
        # rather than every caller remembering to divide by 100.
        "revenue_naira": revenue_kobo / 100,
        "completions": Enrollment.objects.filter(
            status=Enrollment.Status.COMPLETED, completed_at__gte=yesterday
        ).count(),
    }

    # Self-tuning nudge per build spec §3.3.
    tuning_suggestions = []
    for s in decide_today + watch:
        streak = get_recent_dismissal_streak(s.key)
        if streak >= 3:
            tuning_suggestions.append(f'"{s.key}" has been dismissed {streak} times running — consider raising its threshold or deactivating it.')

    return {
        "decide_today": decide_today,
        "watch": watch,
        "quiet_count": quiet_count,
        "obligations_this_week": obligations_this_week,
        "decisions_due_this_week": decisions_due_this_week,
        "numbers": numbers,
        "tuning_suggestions": tuning_suggestions,
        "is_quiet_day": not decide_today and not obligations_this_week and not decisions_due_this_week,
    }


def send_daily_digest(organization) -> DigestRun:
    today = timezone.now().date()
    existing = DigestRun.objects.filter(organization=organization, run_date=today).first()
    if existing and existing.sent_at:
        return existing  # dedupe_key on the email itself is the real guard; this is a cheap pre-check

    context = build_digest_context(organization)
    html = render_to_string("operations/digest_email.html", context)

    recipient = _ops_recipient(organization)
    signal_count = len(context["decide_today"]) + len(context["watch"]) + context["quiet_count"]

    run, _ = DigestRun.objects.get_or_create(
        organization=organization, run_date=today,
        defaults={"signal_count": signal_count, "rendered_html": html},
    )

    if not recipient:
        return run  # nowhere to send — still keep the record, per §1 "why didn't I know" retrievability

    from apps.engagement.services import send_email

    subject = "Nothing needs a decision today" if context["is_quiet_day"] else f"{len(context['decide_today'])} to decide today"
    log = send_email(
        to_email=recipient, template_key="ops_digest", subject=f"Xpress Academy — {subject}",
        html=html, dedupe_key=f"digest:{today}",
    )
    run.sent_at = timezone.now()
    run.email_log = log
    run.signal_count = signal_count
    run.rendered_html = html
    run.save(update_fields=["sent_at", "email_log", "signal_count", "rendered_html"])
    return run
