import uuid

from django.db import models


class CertificateSignatureMode(models.TextChoices):
    """Shared by Organization and Instructor — how a certificate's
    signature block should render for courses that party signs.
    Deliberately an explicit choice, not something inferred from
    which fields happen to be blank: "I left my name blank" and "I
    chose to not show my name" read the same in the data either way,
    but only one of those is really a decision. Making the mode its
    own field means every person (the platform founder, and every
    marketplace instructor) picks what they want, not what a fallback
    rule guesses they'd want."""

    NAME_TITLE = "NAME_TITLE", "My name and title"
    ORG_NAME_ONLY = "ORG_NAME_ONLY", "Organization name only (no personal name)"
    SIGNATURE_IMAGE = "SIGNATURE_IMAGE", "An uploaded signature image"


class TimeStampedModel(models.Model):
    """Abstract base adding created/updated timestamps to any model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract base giving a model a public-safe UUID identifier
    separate from its integer primary key. Use where the id must
    never leak sequential information (e.g. certificate verification).
    """

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    class Meta:
        abstract = True


class OrganizationOwnedModel(TimeStampedModel):
    """Abstract base for every tenant-owned model in the platform.

    We run exactly one Organization today (Xpress Digital Academy).
    Carrying this FK from migration one means hosting a second
    organization later is a data operation, not a rewrite — see
    ARCHITECTURE.md. Do not build tenant-switching UI yet; just carry
    the key on every model that belongs to a tenant.

    PROTECT (not CASCADE): we must never lose tenant data to a
    careless admin delete of an Organization.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    class Meta:
        abstract = True
