"""Load Selar contacts so the follow-up sequence in
apps.engagement.selar can reach them.

  # Selar dashboard > Sales > "Export Data in CSV"
  python manage.py import_selar_contacts --csv sales.csv

  # From Selar's "You've got an abandoned transaction" email
  python manage.py import_selar_contacts --abandoned "Ayombo Ogunyemi <ayjury2017@gmail.com>"

  # Send whatever is due right away instead of waiting for the daily job
  python manage.py import_selar_contacts --csv sales.csv --send-now

Free-sample rows (total 0) become FREE contacts and paid rows become
PAID. Re-running with the same file is safe: status only moves forward
and every email is deduped.
"""

from django.core.management.base import BaseCommand, CommandError

from apps.engagement.models import SelarContact
from apps.engagement.selar import import_abandoned, import_csv_text, send_selar_followups, unverified_claims


class Command(BaseCommand):
    help = "Import Selar free-sample downloaders, buyers and abandoned checkouts for follow-up emails."

    def add_arguments(self, parser):
        parser.add_argument("--csv", help="Selar Sales CSV export")
        parser.add_argument("--abandoned", action="append", default=[],
                            help='"Full Name <email>" from a Selar abandoned-transaction email (repeatable)')
        parser.add_argument("--send-now", action="store_true", help="Run the follow-up sequence immediately")

    def handle(self, *args, **opts):
        if not opts["csv"] and not opts["abandoned"]:
            raise CommandError("Give --csv and/or --abandoned.")
        counts = {s: 0 for s in SelarContact.Status.values}

        if opts["csv"]:
            with open(opts["csv"], newline="", encoding="utf-8-sig") as fh:
                for status, n in import_csv_text(fh.read()).items():
                    counts[status] += n

        for entry in opts["abandoned"]:
            try:
                import_abandoned(entry)
            except ValueError as exc:
                raise CommandError(str(exc))
            counts[SelarContact.Status.ABANDONED] += 1

        self.stdout.write(f"Imported: {counts}")
        suspicious = list(unverified_claims())
        for c in suspicious:
            self.stdout.write(self.style.WARNING(
                f"UNVERIFIED activation: {c.email} used reference {c.reference} on {c.created_at:%d %b} "
                "and it is not in any imported Selar sales export. Check it on Selar before removing access."
            ))
        if opts["send_now"]:
            self.stdout.write(f"Sent: {send_selar_followups()}")
