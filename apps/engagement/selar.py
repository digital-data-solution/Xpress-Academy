"""Follow-up for people who touched our Selar store.

Selar (selar.com) sells the PSR pack alongside this site's own
checkout, but on the free plan it has no webhooks and its own
abandoned-cart email can't be customised. So contacts come in by
import (see the import_selar_contacts command: Selar's sales CSV export
plus the abandoned-transaction emails Selar sends the merchant), and the
follow-up below runs from the daily scheduled-tasks job, sent from the
academy's own address.

The sequence, counted in days since the contact entered their status:

  FREE       day 2  "how did you score?"   day 5  full-pack offer
  ABANDONED  day 0  "still waiting"        day 2  last reminder
  PAID       day 0  website access (account + PSR course enrollment)

Every step is deduped on EmailLog.dedupe_key, so running the job more
than once a day, or re-importing the same CSV, never double-sends.
Anyone PAID, unsubscribed, or already enrolled in the PSR course on this
site through its own checkout drops out of the sales emails.
"""

import csv
import io
import logging
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from .models import SelarContact
from .services import send_email

logger = logging.getLogger(__name__)

PAID_URL = "https://selar.com/37c32yp3md"
FREE_URL = "https://selar.com/8621772r27"
TEAM_URL = "https://selar.com/78exycg197"
PSR_COURSE_SLUG = "public-service-rules-guide"

# (status, step key, minimum days in status, subject, template)
SEQUENCE = [
    (SelarContact.Status.FREE, "free-score", 2,
     "How did you score on the PSR questions?", "selar_free_score.html"),
    (SelarContact.Status.FREE, "free-offer", 5,
     "Cover the whole PSR section before your exam", "selar_free_offer.html"),
    (SelarContact.Status.ABANDONED, "abandoned-1", 0,
     "Your PSR pack is still waiting for you", "selar_abandoned.html"),
    (SelarContact.Status.ABANDONED, "abandoned-2", 2,
     "Last reminder: your PSR 2021 pack", "selar_abandoned.html"),
]


def record_contact(*, email, name="", phone="", status, when=None) -> SelarContact:
    """Create or move a contact along the funnel. Status only ever moves
    forward (FREE -> ABANDONED -> PAID): re-importing an old free-sample
    row must not drag a paying customer back into the sales sequence."""
    email = email.strip().lower()
    when = when or timezone.now()
    order = [SelarContact.Status.FREE, SelarContact.Status.ABANDONED, SelarContact.Status.PAID]
    contact = SelarContact.objects.filter(email=email).first()
    if contact is None:
        return SelarContact.objects.create(
            email=email, name=name.strip(), phone=phone.strip(), status=status, status_changed_at=when,
        )
    changed = []
    if name and not contact.name:
        contact.name, changed = name.strip(), changed + ["name"]
    if phone and not contact.phone:
        contact.phone, changed = phone.strip(), changed + ["phone"]
    if order.index(status) > order.index(contact.status):
        contact.status, contact.status_changed_at = status, when
        changed += ["status", "status_changed_at"]
    if changed:
        contact.save(update_fields=changed + ["updated_at"])
    return contact


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


def import_csv_text(text) -> dict:
    """Load a Selar Sales CSV export (as text). Free-sample rows
    (total 0) become FREE contacts and paid rows PAID; a paid row's
    order reference confirms any activation-page claim made with it.
    Safe to re-run with the same export."""
    counts = {s: 0 for s in SelarContact.Status.values}
    for row in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        match = EMAIL_RE.search(_col(row, "email"))
        if not match:
            continue
        paid = _amount(_col(row, "total")) > 0
        status = SelarContact.Status.PAID if paid else SelarContact.Status.FREE
        contact = record_contact(
            email=match.group(0), name=_col(row, "fullname") or _col(row, "customer", "name"),
            phone=_col(row, "mobile"), status=status, when=_when(_col(row, "date")),
        )
        counts[status] += 1
        reference = _col(row, "reference").upper()
        if paid and reference:
            SelarContact.objects.filter(reference=reference).update(reference_verified=True)
            if not contact.reference and not SelarContact.objects.filter(reference=reference).exists():
                contact.reference, contact.reference_verified = reference, True
                contact.save(update_fields=["reference", "reference_verified", "updated_at"])
    return counts


def import_abandoned(entry) -> SelarContact:
    """One line from a Selar abandoned-transaction email: "Full Name <email>"."""
    match = EMAIL_RE.search(entry)
    if not match:
        raise ValueError(f"No email address in {entry!r}")
    name = entry[:match.start()].strip(" <\"'")
    return record_contact(email=match.group(0), name=name, status=SelarContact.Status.ABANDONED)



REFERENCE_RE = re.compile(r"^S[A-Z0-9]{10,14}$")


class ClaimError(ValueError):
    pass


def claim_reference(*, email, name, reference) -> SelarContact:
    """The activation page: a Selar buyer swaps their order reference
    for website access (the PSR videos live behind a login rather than
    in the downloadable pack). Access is granted at once and the
    reference is checked against Selar's sales export at the next
    import. Each reference can unlock exactly one email."""
    reference = re.sub(r"\s+", "", reference or "").upper()
    email = email.strip().lower()
    if not REFERENCE_RE.match(reference):
        raise ClaimError("That doesn't look like a Selar order reference. It starts with S, e.g. S466KF16168BX.")
    taken = SelarContact.objects.filter(reference=reference).exclude(email=email).exists()
    if taken:
        raise ClaimError("This order reference has already been used to activate another account.")
    contact = record_contact(email=email, name=name, status=SelarContact.Status.PAID)
    if not contact.reference:
        contact.reference = reference
        contact.save(update_fields=["reference", "updated_at"])
    grant_site_access(contact)
    return contact


def unverified_claims(*, older_than_days=2):
    cutoff = timezone.now() - timedelta(days=older_than_days)
    return SelarContact.objects.filter(
        status=SelarContact.Status.PAID, reference_verified=False, created_at__lt=cutoff,
    ).exclude(reference="")


def _bought_on_site(email) -> bool:
    from apps.enrollment.models import Enrollment
    return Enrollment.objects.filter(user__email__iexact=email, course__slug=PSR_COURSE_SLUG).exists()


def _context(contact):
    return {"first_name": contact.first_name, "paid_url": PAID_URL, "free_url": FREE_URL, "team_url": TEAM_URL, "is_office": contact.is_office,
            "site_url": settings.SITE_URL}


@transaction.atomic
def grant_site_access(contact: SelarContact):
    """A Selar buyer also gets the PSR course on this site (video player,
    progress, quizzes) at no extra cost. The account has no password
    yet; the email tells them to set one through forgot-password, which
    keeps this path free of any long-lived login token."""
    from apps.accounts.models import User
    from apps.catalog.models import Course
    from apps.payments.services import _create_or_get_enrollment, _grant_included_courses
    from apps.enrollment.models import Enrollment

    course = Course.objects.filter(slug=PSR_COURSE_SLUG).first()
    if course is None:
        logger.error("selar: course %s missing, cannot grant site access to %s", PSR_COURSE_SLUG, contact.email)
        return None
    user = User.objects.filter(email__iexact=contact.email).first()
    if user is None:
        parts = contact.name.split()
        user = User(email=contact.email, first_name=(parts[0] if parts else "")[:150],
                    last_name=" ".join(parts[1:])[:150])
        user.set_unusable_password()
        user.save()
    enrollment, _ = _create_or_get_enrollment(user=user, course=course, source=Enrollment.Source.MANUAL)
    _grant_included_courses(user=user, course=course, source=Enrollment.Source.MANUAL)

    ctx = {**_context(contact), "has_password": user.has_usable_password(), "course_title": course.title}
    transaction.on_commit(lambda: send_email(
        to_email=contact.email, user=user, template_key="selar_buyer_welcome",
        subject="Your PSR video course is ready — Xpress Digital Academy",
        html=render_to_string("emails/selar_buyer_welcome.html", ctx),
        dedupe_key=f"selar:buyer-welcome:{contact.email}",
    ))
    return enrollment


def send_selar_followups(*, now=None) -> dict:
    now = now or timezone.now()
    sent = {}
    for contact in SelarContact.objects.filter(unsubscribed=False):
        if contact.status == SelarContact.Status.PAID:
            grant_site_access(contact)
            continue
        if _bought_on_site(contact.email):
            continue
        age = now - contact.status_changed_at
        # Only the latest step that is due goes out on a given run. A
        # contact imported days late gets one email, not the whole
        # backlog at once.
        due = [s for s in SEQUENCE if s[0] == contact.status and age >= timedelta(days=s[2])]
        if not due:
            continue
        status, step, _days, subject, template = due[-1]
        key = f"selar:{step}:{contact.email}"
        ctx = {**_context(contact), "is_last": step == "abandoned-2"}
        log = send_email(
            to_email=contact.email, template_key=f"selar_{step}",
            subject=subject.format(first_name=contact.first_name),
            html=render_to_string(f"emails/{template}", ctx), dedupe_key=key,
        )
        sent[step] = sent.get(step, 0) + (log.status == log.Status.SENT)
    return sent
