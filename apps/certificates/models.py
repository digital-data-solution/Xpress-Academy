import uuid

from django.db import models

from apps.common.models import TimeStampedModel


class CertificateSequence(models.Model):
    """Backs atomic serial generation — see services.next_serial().
    One row per (audience_code, year); incremented under
    select_for_update so concurrent issuance can never produce a
    duplicate serial, even though gaps (a failed issuance burning a
    number) are fine and expected."""

    audience_code = models.CharField(max_length=10)
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["audience_code", "year"], name="unique_cert_sequence"),
        ]

    def __str__(self):
        return f"{self.audience_code}-{self.year}: {self.last_number}"


class Certificate(TimeStampedModel):
    # PROTECT: once issued, the Enrollment behind a certificate must
    # not be deletable — this is what "certificates survive account
    # deletion" (build spec §10, NDPR) actually rests on structurally:
    # Enrollment.user is already PROTECT (see apps.enrollment.models),
    # so a User can never be hard-deleted while any Certificate-backing
    # Enrollment exists either. A real account-deletion flow (not yet
    # built) will need to anonymise rather than cascade-delete —
    # learner_name_snapshot below is what makes that possible without
    # breaking verification links, since it doesn't need the User row.
    enrollment = models.OneToOneField(
        "enrollment.Enrollment", on_delete=models.PROTECT, related_name="certificate"
    )

    serial = models.CharField(max_length=50, unique=True, editable=False)
    verification_slug = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    learner_name_snapshot = models.CharField(max_length=255)
    course_title_snapshot = models.CharField(max_length=255)

    issued_at = models.DateTimeField(auto_now_add=True)
    pdf = models.FileField(upload_to="certificates/")
    final_score = models.PositiveIntegerField(null=True, blank=True)

    is_revoked = models.BooleanField(default=False)
    revoked_reason = models.CharField(max_length=255, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.serial} — {self.learner_name_snapshot}"
