from django.core.management.base import BaseCommand

from apps.payments.services import reconcile_pending_payments


class Command(BaseCommand):
    help = (
        "Verify PENDING payments (5min-7day old) against Paystack and grant access to "
        "any that actually succeeded. Meant to run every 10 minutes — see the payments "
        "addendum §2.4. Run on a schedule yourself (Task Scheduler / cron) until Phase 7 "
        "wires this onto Celery beat."
    )

    def handle(self, *args, **options):
        result = reconcile_pending_payments()
        self.stdout.write(self.style.SUCCESS(
            f"Checked {result['checked']}, granted {result['granted']}, "
            f"abandoned {result['abandoned']} (past 7 days)."
        ))
