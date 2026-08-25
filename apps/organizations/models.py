from django.db import models
from django.utils.text import slugify

from apps.common.models import CertificateSignatureMode, TimeStampedModel


class Organization(TimeStampedModel):
    """A tenant on the platform.

    Today there is exactly one row: Xpress Digital Academy. The engine
    is built to host a second organization (e.g. a Bible school) later
    by adding a row here, not by rewriting models. See
    apps.common.models.OrganizationOwnedModel — every tenant-owned
    model across the platform carries a FK to this table.

    No tenant-switching UI is built yet. This model exists so that key
    is already in place when it's needed.
    """

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True)
    primary_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Hex color, e.g. #1A73E8",
    )
    from_email = models.EmailField(
        help_text="Sender address used for all outbound email for this org."
    )
    support_whatsapp = models.CharField(max_length=32, blank=True)

    certificate_signature_mode = models.CharField(
        max_length=20, choices=CertificateSignatureMode.choices, default=CertificateSignatureMode.NAME_TITLE,
        help_text="How the signature block reads on certificates for first-party (non-instructor) courses.",
    )
    certificate_signature_image = models.ImageField(
        upload_to="organizations/signatures/", blank=True, null=True
    )
    certificate_signatory_name = models.CharField(max_length=255, blank=True)
    certificate_signatory_title = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
