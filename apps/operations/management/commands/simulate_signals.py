from django.core.management.base import BaseCommand

from apps.operations.models import Signal
from apps.operations.services import raise_signal
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Fabricates one Signal of each category/severity so the digest and /ops/ queue can be reviewed without waiting for real conditions — build spec §5."

    def handle(self, *args, **options):
        org = Organization.objects.first()
        if not org:
            self.stderr.write("No Organization exists yet — run seed_demo_course first.")
            return

        samples = [
            ("payment.reconcile_mismatch", Signal.Category.MONEY, Signal.Severity.CRITICAL,
             "Paystack shows a paid transaction with no local match: XDA-demo-0001"),
            ("payment.refund_spike", Signal.Category.MONEY, Signal.Severity.URGENT,
             "Refund rate 22% on Practical Dog Breeding over 30 days"),
            ("course.completion_low", Signal.Category.QUALITY, Signal.Severity.ATTENTION,
             "Practical Dog Breeding completion is 11% (4/36)"),
            ("quiz.item_bad", Signal.Category.QUALITY, Signal.Severity.ATTENTION,
             "Question 7 is answered correctly 97% of the time (41 attempts)"),
            ("learner.stalled_cohort", Signal.Category.LEARNER, Signal.Severity.ATTENTION,
             "62% of Founding Cohort inactive 7+ days (8/13)"),
            ("learner.access_expiring_bulk", Signal.Category.LEARNER, Signal.Severity.INFO,
             "6 enrollments expire within 14 days"),
            ("partner.contract_expiring", Signal.Category.PARTNER, Signal.Severity.ATTENTION,
             "Founding Cohort ends 2026-09-20"),
            ("system.cert_expiring", Signal.Category.SYSTEM, Signal.Severity.URGENT,
             "SSL certificate for academy.xpressdigital.ng expires in 14 day(s)"),
            ("legal.obligation_due", Signal.Category.LEGAL, Signal.Severity.CRITICAL,
             "OVERDUE: CAC annual return — due 2026-08-01"),
        ]

        for key, category, severity, title in samples:
            raise_signal(
                organization=org, key=key, category=category, severity=severity, title=title,
                detail="Fabricated by simulate_signals for digest/queue review — not a real condition.",
                recommended_action="This is a demo signal; dismiss it once you've reviewed the layout.",
                dedupe_key=f"demo:{key}",
            )

        self.stdout.write(self.style.SUCCESS(f"Created/updated {len(samples)} demo signals."))
