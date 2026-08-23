"""Signal-generating rules — build spec §2. Each function is called
from tasks.py on its category's schedule and is idempotent (raise_signal
handles dedup). Grouped exactly as the spec groups them.

NOT implemented, and why — flagged here rather than silently missing:

  - Every INSTRUCTOR-category rule, course.review_overdue,
    course.rating_decline, learner.complaint_open, payout.due,
    payment.webhook_failures, legal.agreement_unsigned,
    partner.pilot_midpoint, partner.results_ready — all depend on
    models Phase 10 hasn't built yet (Instructor, CourseReview,
    rating, Complaint, webhook) or, for webhook_failures specifically,
    a webhook that will never exist on this Paystack account at all
    (see ARCHITECTURE.md).
  - system.service_down, system.backup_stale — the app can't reliably
    self-report true downtime (if the process is down, it can't raise
    its own signal) or Supabase's backup status (no API integration
    exists). These need Render's own alerting / an external uptime
    checker / a Supabase backup-status integration — genuinely a
    Phase 9 deploy-infra concern, not something Django code can do by
    itself.
"""

import ssl
import socket
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from apps.catalog.models import Course
from apps.certificates.models import Certificate
from apps.enrollment.models import Cohort, Enrollment
from apps.enrollment.services import get_progress_percent
from apps.organizations.models import Organization
from apps.payments.models import Payment

from .models import CalendarObligation, Signal
from .services import is_rule_active, get_threshold_config, raise_signal


def _org():
    # Single-org today (see apps.organizations) — every rule scopes to it.
    return Organization.objects.first()


# --- MONEY ---------------------------------------------------------

def payment_reconcile_mismatch(reference: str, raw_data: dict):
    """Called from apps.payments.services.sweep_paystack_transactions
    in place of the old ReconciliationFlag stand-in — this IS the
    operations.Signal system that model's docstring said to migrate
    to. CRITICAL, INTERRUPT: a human looks at it, never auto-granted."""
    if not is_rule_active("payment.reconcile_mismatch"):
        return None
    org = _org()
    signal, _ = raise_signal(
        organization=org, key="payment.reconcile_mismatch", category=Signal.Category.MONEY,
        severity=Signal.Severity.CRITICAL,
        title=f"Paystack shows a paid Academy transaction with no local match: {reference}",
        detail=f"Amount: {raw_data.get('amount')}, paid_at: {raw_data.get('paid_at')}.",
        recommended_action="Review the transaction on Paystack and grant access manually via admin "
                            "after confirming it's genuine — do not assume, verify.",
        dedupe_key=f"payment.reconcile_mismatch:{reference}",
        action_url=f"/admin/payments/payment/?q={reference}",
    )
    return signal


def payment_none_today():
    """No successful payment in 72h while at least one course is
    actually for sale — the checkout flow itself may be broken."""
    if not is_rule_active("payment.none_today"):
        return None
    if not Course.objects.filter(is_published=True, price_ngn__gt=0).exists():
        return None
    window = timezone.now() - timezone.timedelta(hours=72)
    if Payment.objects.filter(status=Payment.Status.SUCCESS, paid_at__gte=window).exists():
        return None
    org = _org()
    signal, _ = raise_signal(
        organization=org, key="payment.none_today", category=Signal.Category.MONEY,
        severity=Signal.Severity.ATTENTION,
        title="No successful payments in the last 72 hours",
        detail="At least one course is published and priced, but nothing has sold in 3 days.",
        recommended_action="Check the checkout flow end to end with a real test card, and confirm "
                            "PAYSTACK_SECRET_KEY/PUBLIC_KEY are the right ones for this environment.",
        dedupe_key="payment.none_today",
        action_url="/checkout/",
    )
    return signal


def payment_refund_spike():
    """Refund rate >10% on a course over 30 days."""
    if not is_rule_active("payment.refund_spike"):
        return None
    threshold = get_threshold_config("payment.refund_spike").get("rate_percent", 10)
    window = timezone.now() - timezone.timedelta(days=30)
    org = _org()
    signals = []
    for course in Course.objects.filter(is_published=True):
        payments = Payment.objects.filter(course=course, initialized_at__gte=window)
        success_and_refunded = payments.filter(status__in=[Payment.Status.SUCCESS, Payment.Status.REFUNDED])
        total = success_and_refunded.count()
        if total < 10:  # too small a sample to mean anything
            continue
        refunded = success_and_refunded.filter(status=Payment.Status.REFUNDED).count()
        rate = refunded * 100 / total
        if rate <= threshold:
            continue
        signal, _ = raise_signal(
            organization=org, key="payment.refund_spike", category=Signal.Category.MONEY,
            severity=Signal.Severity.URGENT,
            title=f"Refund rate {rate:.0f}% on {course.title} over 30 days",
            detail=f"{refunded} of {total} payments refunded.",
            recommended_action="Review course quality and the sales page's claims for over-promising.",
            dedupe_key=f"payment.refund_spike:{course.id}",
            action_url=f"/admin/catalog/course/{course.id}/change/",
        )
        signals.append(signal)
    return signals


# --- SYSTEM ---------------------------------------------------------

def system_cert_expiring():
    """Best-effort: only meaningful once SITE_URL is a real https
    domain (Phase 9 deploy) — a no-op against localhost."""
    if not is_rule_active("system.cert_expiring"):
        return None
    parsed = urlparse(settings.SITE_URL)
    if parsed.scheme != "https":
        return None
    threshold_days = get_threshold_config("system.cert_expiring").get("lead_days", 21)
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((parsed.hostname, 443), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=parsed.hostname) as ssock:
                cert = ssock.getpeercert()
        expires = timezone.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        expires = timezone.make_aware(expires, timezone.utc)
    except (socket.error, ssl.SSLError, KeyError, ValueError):
        return None  # can't determine — don't guess, don't false-alarm

    days_left = (expires - timezone.now()).days
    if days_left > threshold_days:
        return None
    org = _org()
    signal, _ = raise_signal(
        organization=org, key="system.cert_expiring", category=Signal.Category.SYSTEM,
        severity=Signal.Severity.URGENT,
        title=f"SSL certificate for {parsed.hostname} expires in {days_left} day(s)",
        detail=f"Expires {expires:%Y-%m-%d}.",
        recommended_action="Renew the certificate — check Render's auto-renewal status first.",
        dedupe_key=f"system.cert_expiring:{expires:%Y-%m}",
    )
    return signal


def system_job_failures(task_name: str, exception_text: str):
    """Called from a Celery task_failure signal receiver (see
    signal_receivers.py) — this is the one rule that's event-driven
    rather than polled on a schedule."""
    if not is_rule_active("system.job_failures"):
        return None
    org = _org()
    if org is None:
        return None
    signal, _ = raise_signal(
        organization=org, key="system.job_failures", category=Signal.Category.SYSTEM,
        severity=Signal.Severity.URGENT,
        title=f"Celery task failing: {task_name}",
        detail=exception_text[:2000],
        recommended_action="Check worker logs for the full traceback.",
        dedupe_key=f"system.job_failures:{task_name}",
    )
    return signal


# --- LEGAL -----------------------------------------------------------

def legal_obligation_due():
    org = _org()
    if org is None:
        return []
    if not is_rule_active("legal.obligation_due"):
        return []
    signals = []
    today = timezone.now().date()
    for obligation in CalendarObligation.objects.filter(organization=org, status=CalendarObligation.Status.PENDING):
        lead_start = obligation.due_date - timezone.timedelta(days=obligation.lead_days)
        if today < lead_start:
            continue
        overdue = today > obligation.due_date
        if overdue and obligation.status != CalendarObligation.Status.OVERDUE:
            obligation.status = CalendarObligation.Status.OVERDUE
            obligation.save(update_fields=["status"])
        signal, _ = raise_signal(
            organization=org, key="legal.obligation_due", category=Signal.Category.LEGAL,
            severity=Signal.Severity.CRITICAL if overdue else Signal.Severity.ATTENTION,
            title=f"{'OVERDUE: ' if overdue else ''}{obligation.title} — due {obligation.due_date}",
            detail=obligation.description,
            recommended_action=f"{obligation.obligation_type.title()} obligation — handle before {obligation.due_date}.",
            dedupe_key=f"legal.obligation_due:{obligation.id}",
            action_url=f"/admin/operations/calendarobligation/{obligation.id}/change/",
            decision_due=obligation.due_date,
        )
        signals.append(signal)
    return signals


# --- QUALITY -----------------------------------------------------------

def course_completion_low():
    if not is_rule_active("course.completion_low"):
        return []
    config = get_threshold_config("course.completion_low")
    min_rate = config.get("min_rate_percent", 15)
    min_enrollments = config.get("min_enrollments", 20)
    days = config.get("sustained_days", 60)

    org = _org()
    signals = []
    for course in Course.objects.filter(is_published=True):
        cutoff = timezone.now() - timezone.timedelta(days=days)
        enrollments = Enrollment.objects.filter(course=course, started_at__lte=cutoff).exclude(
            status=Enrollment.Status.REVOKED
        )
        count = enrollments.count()
        if count < min_enrollments:
            continue
        completed = enrollments.filter(status=Enrollment.Status.COMPLETED).count()
        rate = completed * 100 / count
        if rate >= min_rate:
            continue

        # Find the module with the worst drop-off for the "options" framing.
        worst_module = None
        worst_stall_share = 0
        for module in course.modules.order_by("order"):
            lesson_ids = list(module.lessons.values_list("id", flat=True))
            if not lesson_ids:
                continue
            stalled = 0
            for e in enrollments:
                done = e.lesson_progress.filter(lesson_id__in=lesson_ids, completed_at__isnull=False).count()
                if 0 < done < len(lesson_ids):
                    stalled += 1
            share = stalled / count if count else 0
            if share > worst_stall_share:
                worst_stall_share = share
                worst_module = module

        module_note = f" Drop-off concentrates at {worst_module.title}." if worst_module else ""
        signal, _ = raise_signal(
            organization=org, key="course.completion_low", category=Signal.Category.QUALITY,
            severity=Signal.Severity.ATTENTION,
            title=f"{course.title} completion is {rate:.0f}% ({completed}/{count})",
            detail=f"Sustained low completion over {days} days.{module_note}",
            recommended_action=(
                "(a) Re-record the weak module — highest cost, addresses the likely cause. "
                "(b) Split it into shorter lessons — cheap, often sufficient for length-driven drop-off. "
                "(c) Add a mid-module quiz checkpoint — cheapest, weakest effect. "
                "(d) Accept and monitor — valid if the course is near end of life."
            ),
            dedupe_key=f"course.completion_low:{course.id}",
            action_url=f"/admin/catalog/course/{course.id}/change/",
        )
        signals.append(signal)
    return signals


def quiz_item_bad():
    """A question <20% or >95% correct across >=30 attempts — broken
    or trivial. How the question bank improves itself over years."""
    if not is_rule_active("quiz.item_bad"):
        return []
    from apps.assessment.models import AttemptAnswer

    config = get_threshold_config("quiz.item_bad")
    min_attempts = config.get("min_attempts", 30)
    low, high = config.get("low_percent", 20), config.get("high_percent", 95)

    org = _org()
    signals = []
    stats = (
        AttemptAnswer.objects.values("question_id")
        .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
        .filter(total__gte=min_attempts)
    )
    for row in stats:
        rate = row["correct"] * 100 / row["total"]
        if low <= rate <= high:
            continue
        signal, _ = raise_signal(
            organization=org, key="quiz.item_bad", category=Signal.Category.QUALITY,
            severity=Signal.Severity.ATTENTION,
            title=f"Question {row['question_id']} is answered correctly {rate:.0f}% of the time ({row['total']} attempts)",
            detail="Too easy or too hard to be discriminating — likely broken or trivial.",
            recommended_action="Revise the question/explanation, or retire it (set is_active=False).",
            dedupe_key=f"quiz.item_bad:{row['question_id']}",
            action_url=f"/admin/assessment/question/{row['question_id']}/change/",
        )
        signals.append(signal)
    return signals


# --- LEARNER -----------------------------------------------------------

def learner_stalled_cohort():
    if not is_rule_active("learner.stalled_cohort"):
        return []
    threshold_pct = get_threshold_config("learner.stalled_cohort").get("stalled_share_percent", 40)
    org = _org()
    signals = []
    for cohort in Cohort.objects.all():
        enrollments = cohort.enrollments.filter(status=Enrollment.Status.ACTIVE)
        count = enrollments.count()
        if count < 3:
            continue
        stale = timezone.now() - timezone.timedelta(days=7)
        stalled = enrollments.filter(Q(last_activity_at__lte=stale) | Q(last_activity_at__isnull=True)).count()
        share = stalled * 100 / count
        if share < threshold_pct:
            continue
        signal, _ = raise_signal(
            organization=org, key="learner.stalled_cohort", category=Signal.Category.LEARNER,
            severity=Signal.Severity.ATTENTION,
            title=f"{share:.0f}% of {cohort.name} inactive 7+ days ({stalled}/{count})",
            detail="Structural, not individual — a cohort-wide pattern usually means an accountability gap.",
            recommended_action="Check the accountability arrangement with the institution/instructor, "
                                "not the individual students.",
            dedupe_key=f"learner.stalled_cohort:{cohort.id}",
            action_url=f"/admin/enrollment/cohort/{cohort.id}/change/",
        )
        signals.append(signal)
    return signals


def learner_access_expiring_bulk():
    if not is_rule_active("learner.access_expiring_bulk"):
        return None
    min_count = get_threshold_config("learner.access_expiring_bulk").get("min_count", 5)
    window = timezone.now() + timezone.timedelta(days=14)
    org = _org()
    expiring = Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE, expires_at__isnull=False, expires_at__lte=window,
    )
    count = expiring.count()
    if count < min_count:
        return None
    today = timezone.now().date()
    signal, _ = raise_signal(
        organization=org, key="learner.access_expiring_bulk", category=Signal.Category.LEARNER,
        severity=Signal.Severity.INFO,
        title=f"{count} enrollments expire within 14 days",
        detail="A renewal-campaign opportunity, not a problem.",
        recommended_action="Consider a renewal email or discount push.",
        dedupe_key=f"learner.access_expiring_bulk:{today:%Y-%W}",
    )
    return signal


def learner_certificate_stuck():
    """All lessons complete, final assessment unattempted 14+ days —
    could be genuine hesitation, could be an access bug."""
    if not is_rule_active("learner.certificate_stuck"):
        return []
    from apps.assessment.models import Attempt, Quiz

    org = _org()
    signals = []
    cutoff = timezone.now() - timezone.timedelta(days=14)
    candidates = Enrollment.objects.filter(
        status=Enrollment.Status.ACTIVE, course__requires_final_assessment=True, started_at__lte=cutoff,
    ).select_related("course")

    for enrollment in candidates:
        all_lessons = [l for m in enrollment.course.modules.all() for l in m.lessons.all()]
        if not all_lessons:
            continue
        all_done = all(
            enrollment.lesson_progress.filter(lesson=l, completed_at__isnull=False).exists() for l in all_lessons
        )
        if not all_done:
            continue
        final_quiz = Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=enrollment.course).first()
        if not final_quiz:
            continue
        if Attempt.objects.filter(enrollment=enrollment, quiz=final_quiz).exists():
            continue  # they've at least started it
        signal, _ = raise_signal(
            organization=org, key="learner.certificate_stuck", category=Signal.Category.LEARNER,
            severity=Signal.Severity.INFO,
            title=f"{enrollment.user.email} finished all lessons in {enrollment.course.title} but hasn't attempted the final",
            detail="14+ days since course started, all lessons done, final assessment never opened.",
            recommended_action="Nudge directly, or check the final-assessment link actually works for them.",
            dedupe_key=f"learner.certificate_stuck:{enrollment.id}",
            action_url=f"/admin/enrollment/enrollment/{enrollment.id}/change/",
        )
        signals.append(signal)
    return signals


# --- PARTNER -----------------------------------------------------------

def partner_contract_expiring():
    """Approximated via Cohort.ends_at — there's no dedicated
    institutional-contract model yet, and Cohort already carries the
    scheduling data a partner deal would hang off of."""
    if not is_rule_active("partner.contract_expiring"):
        return []
    lead_days = get_threshold_config("partner.contract_expiring").get("lead_days", 45)
    window = timezone.now() + timezone.timedelta(days=lead_days)
    org = _org()
    signals = []
    for cohort in Cohort.objects.filter(ends_at__isnull=False, ends_at__lte=window, ends_at__gte=timezone.now()):
        signal, _ = raise_signal(
            organization=org, key="partner.contract_expiring", category=Signal.Category.PARTNER,
            severity=Signal.Severity.ATTENTION,
            title=f"{cohort.name} ends {cohort.ends_at:%Y-%m-%d}",
            detail="Renewal conversations on an institutional/cohort deal decide on an annual cycle — late is dead.",
            recommended_action="Start the renewal conversation now.",
            dedupe_key=f"partner.contract_expiring:{cohort.id}",
            action_url=f"/admin/enrollment/cohort/{cohort.id}/change/",
        )
        signals.append(signal)
    return signals


def partner_engagement_low():
    if not is_rule_active("partner.engagement_low"):
        return []
    threshold = get_threshold_config("partner.engagement_low").get("min_completion_percent", 50)
    org = _org()
    signals = []
    for cohort in Cohort.objects.all():
        enrollments = list(cohort.enrollments.filter(status__in=[Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED]))
        if len(enrollments) < 3:
            continue
        # Only meaningful once the cohort is at/past its midpoint.
        if cohort.ends_at:
            total_span = (cohort.ends_at - cohort.starts_at).total_seconds()
            elapsed = (timezone.now() - cohort.starts_at).total_seconds()
            if total_span <= 0 or elapsed < total_span / 2:
                continue
        avg_progress = sum(get_progress_percent(e) for e in enrollments) / len(enrollments)
        if avg_progress >= threshold:
            continue
        signal, _ = raise_signal(
            organization=org, key="partner.engagement_low", category=Signal.Category.PARTNER,
            severity=Signal.Severity.ATTENTION,
            title=f"{cohort.name} average progress {avg_progress:.0f}% at midpoint",
            detail=f"{len(enrollments)} learners.",
            recommended_action="Escalate to the institution's contact, not the students directly.",
            dedupe_key=f"partner.engagement_low:{cohort.id}",
            action_url=f"/admin/enrollment/cohort/{cohort.id}/change/",
        )
        signals.append(signal)
    return signals
