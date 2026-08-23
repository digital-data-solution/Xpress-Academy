"""Signal lifecycle — raise/acknowledge/snooze/resolve/dismiss. Every
rule in rules.py calls raise_signal(); nothing else creates a Signal
row, same one-choke-point discipline as send_email() and the Paystack
gateway elsewhere in this codebase.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import Signal, SignalRule


@transaction.atomic
def raise_signal(
    *, organization, key, category, severity, title, detail, recommended_action,
    dedupe_key, action_url="", subject=None, decision_due=None,
):
    """Idempotent per build spec §1: "If a rule fires again for an
    already-open signal, increment occurrence_count and update
    last_seen_at — do not create a second row and do not re-notify
    unless severity has escalated." """
    existing = Signal.objects.filter(
        dedupe_key=dedupe_key
    ).exclude(status__in=[Signal.Status.RESOLVED, Signal.Status.DISMISSED]).first()

    if existing:
        escalated = _severity_rank(severity) > _severity_rank(existing.severity)
        existing.occurrence_count += 1
        existing.last_seen_at = timezone.now()
        update_fields = ["occurrence_count", "last_seen_at", "updated_at"]
        if escalated:
            existing.severity = severity
            existing.title = title
            existing.detail = detail
            update_fields += ["severity", "title", "detail"]
        # A snoozed signal that re-fires and escalates should surface again.
        if escalated and existing.status == Signal.Status.SNOOZED:
            existing.status = Signal.Status.OPEN
            existing.snoozed_until = None
            update_fields += ["status", "snoozed_until"]
        existing.save(update_fields=update_fields)
        if escalated:
            transaction.on_commit(lambda: maybe_send_interrupt(existing))
        return existing, escalated

    signal = Signal.objects.create(
        organization=organization, key=key, category=category, severity=severity,
        title=title, detail=detail, recommended_action=recommended_action,
        action_url=action_url, dedupe_key=dedupe_key, decision_due=decision_due,
        **_subject_kwargs(subject),
    )
    transaction.on_commit(lambda: maybe_send_interrupt(signal))
    return signal, True  # "escalated" doubles as "is new" for the interrupt-eligibility check


MAX_INTERRUPTS_PER_DAY = 3


def maybe_send_interrupt(signal: Signal) -> bool:
    """build spec §3.2: interrupts are CRITICAL-only, on a rule
    explicitly marked INTERRUPT channel, hard-capped at 3/day. Past
    the cap, the signal just waits for the next digest — never spam
    past the limit trying to get through anyway."""
    if signal.severity != Signal.Severity.CRITICAL:
        return False
    rule = SignalRule.objects.filter(key=signal.key).first()
    if not rule or rule.channel != SignalRule.Channel.INTERRUPT:
        return False

    if not _reserve_interrupt_budget(signal.organization):
        return False  # cap reached — enforced atomically, see InterruptBudget

    recipient = _ops_recipient(signal.organization)
    if not recipient:
        return False  # no OPS_ALERT_EMAIL and no superuser to fall back to — nothing to send to

    from apps.engagement.services import send_email

    send_email(
        to_email=recipient,
        template_key="ops_interrupt",
        subject=f"[URGENT] {signal.title}",
        html=f"<p><strong>{signal.title}</strong></p><p>{signal.detail}</p><p>{signal.recommended_action}</p>",
        dedupe_key=f"interrupt:{signal.id}:{signal.occurrence_count}",
    )
    from .models import InterruptLog
    InterruptLog.objects.create(organization=signal.organization, signal=signal)
    return True


@transaction.atomic
def _reserve_interrupt_budget(organization) -> bool:
    """Atomically checks-and-increments today's interrupt count under
    select_for_update() — same pattern as
    apps.certificates.services.next_serial(). Returns True (and
    reserves a slot) iff under the cap; False means the cap is
    already spent for today. This must be the ONLY thing that decides
    whether an interrupt goes out — a separate count-then-create is
    racy under real concurrent Celery workers, not just in tests."""
    from .models import InterruptBudget

    today = timezone.now().date()
    budget, _ = InterruptBudget.objects.select_for_update().get_or_create(
        organization=organization, date=today
    )
    if budget.count >= MAX_INTERRUPTS_PER_DAY:
        return False
    budget.count += 1
    budget.save(update_fields=["count"])
    return True


def _ops_recipient(organization) -> str | None:
    """Never hardcode a person's address in source — see
    settings.OPS_ALERT_EMAIL's comment. Falls back to the first
    superuser so the digest/interrupt pipeline still works out of the
    box in dev without that env var set."""
    from django.conf import settings

    if settings.OPS_ALERT_EMAIL:
        return settings.OPS_ALERT_EMAIL
    from apps.accounts.models import User
    superuser = User.objects.filter(is_superuser=True, is_active=True).order_by("id").first()
    return superuser.email if superuser else None


def _subject_kwargs(subject):
    if subject is None:
        return {}
    return {"subject_type": ContentType.objects.get_for_model(subject), "subject_id": subject.pk}


_SEVERITY_RANK = {"INFO": 0, "ATTENTION": 1, "URGENT": 2, "CRITICAL": 3}


def _severity_rank(severity):
    return _SEVERITY_RANK.get(severity, 0)


def is_rule_active(key: str) -> bool:
    rule = SignalRule.objects.filter(key=key).first()
    return rule is None or rule.is_active  # no rule row yet = fail open, don't silently drop a new rule


def get_threshold_config(key: str) -> dict:
    rule = SignalRule.objects.filter(key=key).first()
    return rule.threshold_config if rule else {}


def acknowledge_signal(signal: Signal, user=None) -> Signal:
    signal.status = Signal.Status.ACKNOWLEDGED
    signal.save(update_fields=["status", "updated_at"])
    return signal


def snooze_signal(signal: Signal, days: int) -> Signal:
    signal.status = Signal.Status.SNOOZED
    signal.snoozed_until = timezone.now() + timezone.timedelta(days=days)
    signal.save(update_fields=["status", "snoozed_until", "updated_at"])
    return signal


def resolve_signal(signal: Signal, user=None) -> Signal:
    signal.status = Signal.Status.RESOLVED
    signal.resolved_at = timezone.now()
    signal.resolved_by = user
    signal.save(update_fields=["status", "resolved_at", "resolved_by", "updated_at"])
    return signal


def dismiss_signal(signal: Signal, reason: str, user=None) -> Signal:
    signal.status = Signal.Status.DISMISSED
    signal.resolved_at = timezone.now()
    signal.resolved_by = user
    signal.dismissal_reason = reason
    signal.save(update_fields=["status", "resolved_at", "resolved_by", "dismissal_reason", "updated_at"])
    return signal


def unsnooze_expired_signals() -> int:
    """A snoozed signal past its snoozed_until reverts to OPEN so it
    shows up in the queue/digest again."""
    return Signal.objects.filter(
        status=Signal.Status.SNOOZED, snoozed_until__lte=timezone.now(),
    ).update(status=Signal.Status.OPEN, snoozed_until=None)


def get_open_signals(organization, category=None):
    qs = Signal.objects.filter(organization=organization).exclude(
        status__in=[Signal.Status.RESOLVED, Signal.Status.DISMISSED, Signal.Status.SNOOZED]
    )
    if category:
        qs = qs.filter(category=category)
    return qs.order_by("-severity", "-last_seen_at")


def get_recent_dismissal_streak(key: str, last_n: int = 3) -> int:
    """build spec §3.3: "Track dismissals per rule. If a rule is
    dismissed three times running, the digest says so." Returns how
    many of the most recent `last_n` resolutions for this rule's
    signals were dismissals (0 if the streak is broken by a real
    resolve, or fewer than last_n exist)."""
    recent = list(
        Signal.objects.filter(key=key, status__in=[Signal.Status.RESOLVED, Signal.Status.DISMISSED])
        .order_by("-resolved_at")[:last_n]
    )
    streak = 0
    for s in recent:
        if s.status != Signal.Status.DISMISSED:
            break
        streak += 1
    return streak
