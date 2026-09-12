"""Bulk institutional enrolment from CSV — the 'N student seats' side
of build spec §B. Deliberately mirrors apps.assessment.csv_import's
house style (a result dataclass, per-row validation and errors, never
let one bad row silently kill the whole batch).

Expected columns (header row required, extras ignored): email,
first_name, last_name. One row per student.

A "seat" here means a student getting institutional access to the
licence's whole course bundle, not one seat per course — so a student
who already has independent access to every course in the bundle
(bought it themselves, say) consumes zero seats when imported; a
partial overlap fills in only the missing course(s) without ever
touching their existing enrollment for the course(s) they already
have some other way (see the per-course existing-enrollment check
below — an institutional import must never silently downgrade or
shorten an enrollment someone already paid for directly).

Enforces the licence's seat cap: stops accepting new rows once
seats_remaining hits 0 for that run. Every brand-new user account gets
set_unusable_password() plus the existing password-reset email flow so
they have a working login — no separate invite system built,
deliberately reusing what already exists (see
apps.accounts.views._send_password_reset_email) rather than
duplicating token-signing/expiry logic that's already correct.

NOT wrapped in one outer transaction.atomic() across the whole file on
purpose: a bad row further down a long CSV must not silently roll back
every already-succeeded row above it — each row commits independently
(same "don't lose progress" reasoning this platform applies to answer
saving and content-version snapshots elsewhere).
"""
import csv
import io
from dataclasses import dataclass, field

from django.db import transaction

from apps.accounts.models import User
from apps.enrollment.models import Enrollment

from .models import InstitutionalLicense


@dataclass
class BulkEnrollResult:
    created: int = 0                # brand-new user account + seat
    seated_existing_user: int = 0   # pre-existing user, new seat under this licence
    already_seated: int = 0         # already holds a seat under this licence — no-op
    errors: list[str] = field(default_factory=list)


def bulk_enroll_students_from_csv(license: InstitutionalLicense, file_obj) -> BulkEnrollResult:
    result = BulkEnrollResult()

    if license.status != InstitutionalLicense.Status.ACTIVE:
        result.errors.append(
            f"This licence is {license.get_status_display()}, not Active — mark it Active (payment confirmed) "
            "before importing students."
        )
        return result

    raw = file_obj.read()
    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        result.errors.append("File appears to be empty or not a CSV.")
        return result

    required = {"email"}
    missing = required - set(f.strip() for f in reader.fieldnames)
    if missing:
        result.errors.append(f"Missing required column(s): {', '.join(sorted(missing))}")
        return result

    courses = list(license.courses.all())
    if not courses:
        result.errors.append("This licence has no courses attached — add at least one before importing students.")
        return result

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        email = (row.get("email") or "").strip().lower()
        if not email:
            continue  # silently skip blank rows

        if license.seats_remaining <= 0:
            result.errors.append(f"Row {i} ({email}): seat cap reached ({license.seats} seats) — skipped.")
            continue

        first_name = (row.get("first_name") or "").strip()
        last_name = (row.get("last_name") or "").strip()

        try:
            with transaction.atomic():
                user, user_created = User.objects.get_or_create(
                    email=email,
                    defaults={"first_name": first_name, "last_name": last_name},
                )
                if user_created:
                    user.set_unusable_password()
                    user.save(update_fields=["password"])

                already_seated = Enrollment.objects.filter(
                    user=user, institutional_license=license
                ).exists()
                if already_seated:
                    result.already_seated += 1
                    continue

                for course in courses:
                    # Never overwrite an enrollment the student already
                    # has some other way (e.g. they bought the course
                    # directly) — only fill in courses they don't have
                    # access to yet.
                    if Enrollment.objects.filter(user=user, course=course).exists():
                        continue
                    Enrollment.objects.create(
                        user=user, course=course,
                        source=Enrollment.Source.INSTITUTIONAL,
                        institutional_license=license,
                        expires_at=license.term_ends_at,
                        status=Enrollment.Status.ACTIVE,
                    )
        except Exception as exc:  # one malformed row must not kill the whole batch
            result.errors.append(f"Row {i} ({email}): {exc}")
            continue

        if already_seated:
            continue
        if user_created:
            from apps.accounts.views import _send_password_reset_email

            _send_password_reset_email(user)
            result.created += 1
        else:
            result.seated_existing_user += 1

    return result
