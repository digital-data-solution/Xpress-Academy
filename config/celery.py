"""Celery app — build spec §7. The broker is Redis (REDIS_URL).

The task functions this schedule calls mostly wrap logic that already
existed and worked before Celery did: `expire_attempt_if_stale`
(Phase 4), `issue_certificate` (Phase 5), and
`reconcile_pending_payments`/`sweep_paystack_transactions` (Phase 6,
previously only reachable as management commands — this is what
finally puts them on the schedule the payments addendum called for).
Phase 7 adds the schedule, not new business logic, for those.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("xpress_academy")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# All times are WAT (Africa/Lagos) — settings.TIME_ZONE, and
# CELERY_TIMEZONE below is pinned to match so the times below mean
# what they say for a Nigerian audience, not UTC.
app.conf.beat_schedule = {
    "unlock-dripped-modules": {
        "task": "apps.engagement.tasks.unlock_dripped_modules",
        "schedule": crontab(minute=0),  # hourly
    },
    "detect-stalled-learners": {
        "task": "apps.engagement.tasks.detect_stalled_learners",
        "schedule": crontab(hour=9, minute=0),  # daily 09:00 WAT
    },
    "warn-expiring-access": {
        "task": "apps.engagement.tasks.warn_expiring_access",
        "schedule": crontab(hour=8, minute=0),  # daily
    },
    "expire-enrollments": {
        "task": "apps.engagement.tasks.expire_enrollments",
        "schedule": crontab(hour=1, minute=0),  # daily
    },
    "remind-live-session": {
        "task": "apps.engagement.tasks.remind_live_session",
        "schedule": crontab(minute=0),  # hourly
    },
    "expire-stale-attempts": {
        "task": "apps.engagement.tasks.expire_stale_attempts",
        "schedule": crontab(minute="*/15"),
    },
    "reconcile-pending-payments": {
        "task": "apps.engagement.tasks.reconcile_pending_payments_task",
        "schedule": crontab(minute="*/10"),
    },
    "sweep-paystack-transactions": {
        "task": "apps.engagement.tasks.sweep_paystack_transactions_task",
        "schedule": crontab(hour=2, minute=0),  # daily 02:00 WAT
    },
    # --- Phase 11: operations/signals — build spec §5, "money hourly,
    # quality nightly, growth weekly" ---
    "ops-evaluate-money-rules": {
        "task": "apps.operations.tasks.evaluate_money_rules",
        "schedule": crontab(minute=0),  # hourly
    },
    "ops-evaluate-system-and-legal-rules": {
        "task": "apps.operations.tasks.evaluate_system_and_legal_rules",
        "schedule": crontab(hour=3, minute=0),  # daily
    },
    "ops-evaluate-quality-rules": {
        "task": "apps.operations.tasks.evaluate_quality_rules",
        "schedule": crontab(hour=4, minute=0),  # nightly
    },
    "ops-evaluate-learner-rules": {
        "task": "apps.operations.tasks.evaluate_learner_rules",
        "schedule": crontab(hour=4, minute=30),  # nightly
    },
    "ops-evaluate-partner-rules": {
        "task": "apps.operations.tasks.evaluate_partner_rules",
        "schedule": crontab(hour=5, minute=0),  # nightly
    },
    "ops-expire-snoozed-signals": {
        "task": "apps.operations.tasks.expire_snoozed_signals",
        "schedule": crontab(minute=0),  # hourly
    },
    "ops-send-digest": {
        "task": "apps.operations.tasks.send_digest",
        "schedule": crontab(hour=7, minute=0),  # daily 07:00 WAT, per §3.1
    },
}
