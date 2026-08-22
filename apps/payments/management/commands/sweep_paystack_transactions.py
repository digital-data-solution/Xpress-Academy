from django.core.management.base import BaseCommand

from apps.payments.services import sweep_paystack_transactions


class Command(BaseCommand):
    help = (
        "List the last 48h of successful Paystack transactions, filter to Academy-tagged "
        "ones, and flag (never auto-grant) any with no matching local SUCCESS payment. "
        "Meant to run daily at 02:00 WAT — see the payments addendum §2.4. This is the "
        "safety net that would have caught a missed payment entirely; run it on a schedule "
        "yourself until Phase 7 wires this onto Celery beat."
    )

    def handle(self, *args, **options):
        result = sweep_paystack_transactions()
        if result["flagged"]:
            self.stdout.write(self.style.WARNING(
                f"Saw {result['seen']} Academy transaction(s), flagged {result['flagged']} "
                f"mismatch(es) for review in admin (ReconciliationFlag)."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Saw {result['seen']} Academy transaction(s), no mismatches."
            ))
