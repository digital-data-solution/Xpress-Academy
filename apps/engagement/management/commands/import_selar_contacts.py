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

import csv
import re
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.engagement.models import SelarContact
from apps.engagement.selar import record_contact, send_selar_followups, unverified_claims

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _col(row, *needles):
    for key, value in row.items():
        if key and all(n in key.lower() for n in needles):
            return (value or "").strip()
    return ""


def _amount(text):
    digits = re.sub(r"[^\d.]", "", text or "")
    return float(digits) if digits else 0.0


def _when(text):
    # Selar shows e.g. "Oct 22nd 2026, 11:50 AM"; fall back to now if the export format differs.
    cleaned = re.sub(r"(\d)(st|nd|rd|th)", r"\1", text or "")
    for fmt in ("%b %d %Y, %I:%M %p", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return timezone.make_aware(datetime.strptime(cleaned, fmt))
        except ValueError:
            continue
    return timezone.now()


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
                for row in csv.DictReader(fh):
                    match = EMAIL_RE.search(_col(row, "email"))
                    if not match:
                        continue
                    paid = _amount(_col(row, "total")) > 0
                    status = SelarContact.Status.PAID if paid else SelarContact.Status.FREE
                    contact = record_contact(
                        email=match.group(0), name=_col(row, "fullname") or _col(row, "customer", "name"), phone=_col(row, "mobile"),
                        status=status, when=_when(_col(row, "date")),
                    )
                    counts[status] += 1
                    reference = _col(row, "reference").upper()
                    if paid and reference:
                        # Confirms an activation-page claim made with this
                        # reference, whichever email it was claimed with.
                        SelarContact.objects.filter(reference=reference).update(reference_verified=True)
                        if not contact.reference and not SelarContact.objects.filter(reference=reference).exists():
                            contact.reference, contact.reference_verified = reference, True
                            contact.save(update_fields=["reference", "reference_verified", "updated_at"])

        for entry in opts["abandoned"]:
            match = EMAIL_RE.search(entry)
            if not match:
                raise CommandError(f"No email address in {entry!r}")
            name = entry[:match.start()].strip(" <\"'")
            record_contact(email=match.group(0), name=name, status=SelarContact.Status.ABANDONED)
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
