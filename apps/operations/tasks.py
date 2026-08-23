"""Scheduled per build spec §5: "money hourly, quality nightly, growth
weekly." Wired onto config/celery.py's beat_schedule."""

from celery import shared_task

from apps.organizations.models import Organization

from . import rules
from .digest import send_daily_digest
from .services import unsnooze_expired_signals


@shared_task
def evaluate_money_rules():
    rules.payment_none_today()
    rules.payment_refund_spike()
    # payment.reconcile_mismatch is event-driven, called directly from
    # apps.payments.services.sweep_paystack_transactions — not polled here.


@shared_task
def evaluate_system_and_legal_rules():
    rules.system_cert_expiring()
    rules.legal_obligation_due()


@shared_task
def evaluate_quality_rules():
    rules.course_completion_low()
    rules.quiz_item_bad()


@shared_task
def evaluate_learner_rules():
    rules.learner_stalled_cohort()
    rules.learner_access_expiring_bulk()
    rules.learner_certificate_stuck()


@shared_task
def evaluate_partner_rules():
    rules.partner_contract_expiring()
    rules.partner_engagement_low()


@shared_task
def send_digest():
    for org in Organization.objects.filter(is_active=True):
        send_daily_digest(org)


@shared_task
def expire_snoozed_signals():
    return unsnooze_expired_signals()
