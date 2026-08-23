"""Seeds sensible default thresholds — build spec §1: "Ship sensible
defaults via a data migration." Everything here is editable in admin
from this point on without a deploy; these are starting points, not
sacred numbers.
"""

from django.db import migrations

DEFAULT_RULES = [
    # key, category, default_severity, channel, cooldown_days, threshold_config, description
    ("payment.reconcile_mismatch", "MONEY", "CRITICAL", "INTERRUPT", 0, {},
     "Paystack shows a paid Academy transaction with no matching local SUCCESS payment."),
    ("payment.none_today", "MONEY", "ATTENTION", "DIGEST", 1, {},
     "No successful payment in 72h while a priced course is published."),
    ("payment.refund_spike", "MONEY", "URGENT", "DIGEST", 7, {"rate_percent": 10},
     "Refund rate exceeds threshold on a course over the trailing 30 days."),
    ("system.cert_expiring", "SYSTEM", "URGENT", "INTERRUPT", 1, {"lead_days": 21},
     "SSL certificate for SITE_URL expiring soon."),
    ("system.job_failures", "SYSTEM", "URGENT", "DIGEST", 1, {},
     "A Celery task raised an exception."),
    ("legal.obligation_due", "LEGAL", "ATTENTION", "DIGEST", 1, {},
     "A CalendarObligation has entered its lead window (or is overdue, which escalates to CRITICAL)."),
    ("course.completion_low", "QUALITY", "ATTENTION", "DIGEST", 14,
     {"min_rate_percent": 15, "min_enrollments": 20, "sustained_days": 60},
     "Sustained low completion on a published course with enough enrollments to mean something."),
    ("quiz.item_bad", "QUALITY", "ATTENTION", "DIGEST", 14,
     {"min_attempts": 30, "low_percent": 20, "high_percent": 95},
     "A question is answered correctly too rarely or too often to be discriminating."),
    ("learner.stalled_cohort", "LEARNER", "ATTENTION", "DIGEST", 7, {"stalled_share_percent": 40},
     "A large share of a cohort has gone quiet — usually structural, not individual."),
    ("learner.access_expiring_bulk", "LEARNER", "INFO", "DIGEST", 7, {"min_count": 5},
     "A meaningful number of enrollments expire within 14 days — a renewal-campaign opportunity."),
    ("learner.certificate_stuck", "LEARNER", "INFO", "DIGEST", 14, {},
     "All lessons complete, final assessment never attempted after 14+ days."),
    ("partner.contract_expiring", "PARTNER", "ATTENTION", "DIGEST", 14, {"lead_days": 45},
     "A cohort (proxy for an institutional deal) ends within the lead window."),
    ("partner.engagement_low", "PARTNER", "ATTENTION", "DIGEST", 14, {"min_completion_percent": 50},
     "A cohort's average progress is below threshold at its midpoint."),
]


def seed(apps, schema_editor):
    SignalRule = apps.get_model("operations", "SignalRule")
    for key, category, severity, channel, cooldown, config, description in DEFAULT_RULES:
        SignalRule.objects.update_or_create(
            key=key,
            defaults={
                "category": category, "default_severity": severity, "channel": channel,
                "cooldown_days": cooldown, "threshold_config": config, "description": description,
                "is_active": True,
            },
        )


def unseed(apps, schema_editor):
    SignalRule = apps.get_model("operations", "SignalRule")
    SignalRule.objects.filter(key__in=[r[0] for r in DEFAULT_RULES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
