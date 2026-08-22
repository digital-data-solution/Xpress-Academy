import uuid

from django.db import models


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
