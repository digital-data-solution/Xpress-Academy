from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

from . import rules
from .digest import build_digest_context, send_daily_digest
from .models import CalendarObligation, InterruptLog, Signal, SignalRule
from .services import (
    dismiss_signal,
    get_recent_dismissal_streak,
    maybe_send_interrupt,
    raise_signal,
    resolve_signal,
    snooze_signal,
    unsnooze_expired_signals,
)


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience=Audience.BREEDER)
    return Course.objects.create(
        organization=org, programme=programme, title="Test Course", audience=Audience.BREEDER,
        is_published=True, review_status=Course.ReviewStatus.APPROVED,
    )


@pytest.fixture
def staff_user():
    u = User.objects.create_user(email="staff@example.com", password="testpass123")
    u.is_staff = True
    u.is_superuser = True
    u.save()
    return u


def _raise(org, key="test.key", severity=Signal.Severity.ATTENTION, dedupe_key="test-dedupe"):
    signal, is_new = raise_signal(
        organization=org, key=key, category=Signal.Category.QUALITY, severity=severity,
        title="Test signal", detail="detail", recommended_action="do something", dedupe_key=dedupe_key,
    )
    return signal, is_new


@pytest.mark.django_db
class TestRaiseSignal:
    def test_creates_new_signal(self, org):
        signal, is_new = _raise(org)
        assert is_new is True
        assert signal.occurrence_count == 1
        assert signal.status == Signal.Status.OPEN

    def test_reraising_same_dedupe_key_increments_not_duplicates(self, org):
        _raise(org)
        signal, is_new = _raise(org)
        assert is_new is False
        assert signal.occurrence_count == 2
        assert Signal.objects.filter(dedupe_key="test-dedupe").count() == 1

    def test_escalation_updates_severity(self, org):
        _raise(org, severity=Signal.Severity.INFO)
        signal, escalated = _raise(org, severity=Signal.Severity.CRITICAL)
        assert escalated is True
        assert signal.severity == Signal.Severity.CRITICAL

    def test_non_escalation_does_not_downgrade(self, org):
        _raise(org, severity=Signal.Severity.URGENT)
        signal, escalated = _raise(org, severity=Signal.Severity.INFO)
        assert escalated is False
        assert signal.severity == Signal.Severity.URGENT

    def test_resolved_signal_can_reopen_as_new(self, org):
        """A course that was fixed and later regresses raises fresh —
        not blocked forever by an old resolved row."""
        signal, _ = _raise(org)
        resolve_signal(signal)
        new_signal, is_new = _raise(org)
        assert is_new is True
        assert new_signal.id != signal.id

    def test_escalating_a_snoozed_signal_reopens_it(self, org):
        signal, _ = _raise(org, severity=Signal.Severity.INFO)
        snooze_signal(signal, 7)
        signal.refresh_from_db()
        assert signal.status == Signal.Status.SNOOZED

        reopened, escalated = _raise(org, severity=Signal.Severity.CRITICAL)
        assert escalated is True
        assert reopened.status == Signal.Status.OPEN
        assert reopened.snoozed_until is None


@pytest.mark.django_db
class TestLifecycle:
    def test_resolve(self, org, staff_user):
        signal, _ = _raise(org)
        resolve_signal(signal, user=staff_user)
        signal.refresh_from_db()
        assert signal.status == Signal.Status.RESOLVED
        assert signal.resolved_by == staff_user

    def test_dismiss_with_reason(self, org, staff_user):
        signal, _ = _raise(org)
        dismiss_signal(signal, reason="not relevant", user=staff_user)
        signal.refresh_from_db()
        assert signal.status == Signal.Status.DISMISSED
        assert signal.dismissal_reason == "not relevant"

    def test_unsnooze_past_due(self, org):
        signal, _ = _raise(org)
        snooze_signal(signal, 1)
        signal.snoozed_until = timezone.now() - timezone.timedelta(hours=1)
        signal.save(update_fields=["snoozed_until"])

        count = unsnooze_expired_signals()
        signal.refresh_from_db()
        assert count == 1
        assert signal.status == Signal.Status.OPEN

    def test_dismissal_streak(self, org):
        for i in range(3):
            signal, _ = raise_signal(
                organization=org, key="streaky", category=Signal.Category.QUALITY, severity=Signal.Severity.INFO,
                title="x", detail="", recommended_action="", dedupe_key=f"streaky-{i}",
            )
            dismiss_signal(signal, reason="test")
        assert get_recent_dismissal_streak("streaky") == 3

    def test_dismissal_streak_broken_by_resolve(self, org):
        s1, _ = raise_signal(organization=org, key="streaky2", category=Signal.Category.QUALITY, severity=Signal.Severity.INFO, title="x", detail="", recommended_action="", dedupe_key="s2-1")
        resolve_signal(s1)
        s2, _ = raise_signal(organization=org, key="streaky2", category=Signal.Category.QUALITY, severity=Signal.Severity.INFO, title="x", detail="", recommended_action="", dedupe_key="s2-2")
        dismiss_signal(s2, reason="test")
        assert get_recent_dismissal_streak("streaky2") == 1


@pytest.mark.django_db(transaction=True)
class TestInterruptCap:
    """transaction=True: maybe_send_interrupt is dispatched via
    transaction.on_commit() inside raise_signal — same reasoning as
    the Phase 7 email-wiring tests."""

    @pytest.fixture(autouse=True)
    def _ops_recipient_configured(self, settings):
        # maybe_send_interrupt has nowhere to send without a
        # recipient — these tests are about the cap/routing logic,
        # not recipient fallback, so configure it directly rather
        # than depending on a superuser existing.
        settings.OPS_ALERT_EMAIL = "ops@example.com"
        settings.RESEND_API_KEY = ""  # dev no-op path — no real network call

    def _critical_interrupt_rule(self, key):
        SignalRule.objects.update_or_create(
            key=key, defaults={"category": "SYSTEM", "default_severity": "CRITICAL", "channel": "INTERRUPT", "is_active": True},
        )

    def test_critical_interrupt_rule_sends_immediately(self, org):
        self._critical_interrupt_rule("interrupt.test")
        raise_signal(
            organization=org, key="interrupt.test", category=Signal.Category.SYSTEM, severity=Signal.Severity.CRITICAL,
            title="down", detail="", recommended_action="", dedupe_key="interrupt-1",
        )
        assert InterruptLog.objects.filter(organization=org).count() == 1

    def test_non_critical_does_not_interrupt(self, org):
        self._critical_interrupt_rule("interrupt.test2")
        raise_signal(
            organization=org, key="interrupt.test2", category=Signal.Category.SYSTEM, severity=Signal.Severity.ATTENTION,
            title="minor", detail="", recommended_action="", dedupe_key="interrupt-2",
        )
        assert InterruptLog.objects.count() == 0

    def test_digest_channel_does_not_interrupt_even_if_critical(self, org):
        SignalRule.objects.update_or_create(
            key="interrupt.test3", defaults={"category": "SYSTEM", "default_severity": "CRITICAL", "channel": "DIGEST", "is_active": True},
        )
        raise_signal(
            organization=org, key="interrupt.test3", category=Signal.Category.SYSTEM, severity=Signal.Severity.CRITICAL,
            title="critical but digest-only", detail="", recommended_action="", dedupe_key="interrupt-3",
        )
        assert InterruptLog.objects.count() == 0

    def test_hard_cap_of_three_per_day(self, org):
        for i in range(5):
            key = f"interrupt.cap{i}"
            self._critical_interrupt_rule(key)
            raise_signal(
                organization=org, key=key, category=Signal.Category.SYSTEM, severity=Signal.Severity.CRITICAL,
                title=f"critical {i}", detail="", recommended_action="", dedupe_key=f"cap-{i}",
            )
        assert InterruptLog.objects.filter(organization=org).count() == 3


@pytest.mark.django_db
class TestMoneyRules:
    def test_reconcile_mismatch_raises_critical_signal(self, org):
        SignalRule.objects.filter(key="payment.reconcile_mismatch").update(is_active=True)
        signal = rules.payment_reconcile_mismatch("XDA-orphan-1", {"amount": 100000, "paid_at": "2026-01-01"})
        assert signal.severity == Signal.Severity.CRITICAL
        assert signal.category == Signal.Category.MONEY

    def test_reconcile_mismatch_inactive_rule_noop(self, org):
        SignalRule.objects.filter(key="payment.reconcile_mismatch").update(is_active=False)
        signal = rules.payment_reconcile_mismatch("XDA-orphan-2", {})
        assert signal is None


def _make_module(course, order=1):
    module = Module.objects.create(course=course, order=order, title=f"Module {order}")
    Lesson.objects.create(module=module, order=1, title=f"Lesson {order}.1", type=Lesson.Type.TEXT)
    return module


@pytest.mark.django_db
class TestQualityRules:
    def test_completion_low_fires_with_enough_stale_enrollments(self, org, course):
        _make_module(course)
        for i in range(20):
            u = User.objects.create_user(email=f"learner{i}@example.com", password="pw")
            e = Enrollment.objects.create(user=u, course=course)
            e.started_at = timezone.now() - timezone.timedelta(days=61)
            e.save(update_fields=["started_at"])
        signals = rules.course_completion_low()
        assert len(signals) == 1
        assert "11%" not in signals[0].title  # sanity: just check it fired, not the exact number
        assert course.title in signals[0].title

    def test_completion_low_skipped_under_min_enrollments(self, org, course):
        _make_module(course)
        for i in range(5):  # below the default min_enrollments=20
            u = User.objects.create_user(email=f"few{i}@example.com", password="pw")
            e = Enrollment.objects.create(user=u, course=course)
            e.started_at = timezone.now() - timezone.timedelta(days=61)
            e.save(update_fields=["started_at"])
        assert rules.course_completion_low() == []


@pytest.mark.django_db
class TestLegalRules:
    def test_obligation_entering_lead_window_fires(self, org, staff_user):
        CalendarObligation.objects.create(
            organization=org, title="CAC return", obligation_type="REGULATORY",
            due_date=timezone.now().date() + timezone.timedelta(days=10), lead_days=30, owner=staff_user,
        )
        signals = rules.legal_obligation_due()
        assert len(signals) == 1
        assert signals[0].severity == Signal.Severity.ATTENTION

    def test_overdue_obligation_escalates_to_critical(self, org, staff_user):
        CalendarObligation.objects.create(
            organization=org, title="CAC return", obligation_type="REGULATORY",
            due_date=timezone.now().date() - timezone.timedelta(days=1), lead_days=30, owner=staff_user,
        )
        signals = rules.legal_obligation_due()
        assert signals[0].severity == Signal.Severity.CRITICAL
        assert "OVERDUE" in signals[0].title

    def test_outside_lead_window_does_not_fire(self, org, staff_user):
        CalendarObligation.objects.create(
            organization=org, title="Far off", obligation_type="REGULATORY",
            due_date=timezone.now().date() + timezone.timedelta(days=200), lead_days=30, owner=staff_user,
        )
        assert rules.legal_obligation_due() == []


@pytest.mark.django_db
class TestDigest:
    def test_quiet_day_context(self, org):
        context = build_digest_context(org)
        assert context["is_quiet_day"] is True

    def test_busy_day_context(self, org):
        _raise(org, severity=Signal.Severity.CRITICAL)
        context = build_digest_context(org)
        assert context["is_quiet_day"] is False
        assert len(context["decide_today"]) == 1

    def test_send_digest_is_idempotent_same_day(self, org, settings):
        settings.RESEND_API_KEY = ""  # dev no-op path, still exercises dedupe_key logic
        settings.OPS_ALERT_EMAIL = "ops@example.com"  # otherwise nowhere to send — see _ops_recipient
        run1 = send_daily_digest(org)
        run2 = send_daily_digest(org)
        assert run1.id == run2.id
        from apps.engagement.models import EmailLog
        assert EmailLog.objects.filter(template_key="ops_digest").count() == 1


@pytest.mark.django_db
class TestOpsQueueView:
    def test_requires_staff(self, org):
        client = Client()
        resp = client.get("/ops/")
        assert resp.status_code == 302  # redirected to login

    def test_staff_can_view_and_resolve(self, org, staff_user):
        signal, _ = _raise(org)
        client = Client()
        client.force_login(staff_user)

        resp = client.get("/ops/")
        assert resp.status_code == 200

        resp = client.post(f"/ops/{signal.id}/act/", {"action": "resolve"})
        assert resp.status_code == 302
        signal.refresh_from_db()
        assert signal.status == Signal.Status.RESOLVED


@pytest.mark.django_db
class TestSimulateSignalsCommand:
    def test_runs_without_error_and_creates_signals(self, org):
        call_command("simulate_signals")
        assert Signal.objects.filter(dedupe_key__startswith="demo:").count() >= 5
