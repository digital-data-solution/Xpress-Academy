from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.catalog.models import Course
from apps.common.models import TimeStampedModel


class Partner(TimeStampedModel):
    """Build spec §9 originally scoped this to veterinary clinics
    (`PartnerClinic`) referring breeders to courses — renamed to
    `Partner` since the referral mechanism is generic and the
    platform's later verticals (JAMB prep, cybersecurity, etc. — see
    Phase 10) will have referral partners that aren't clinics at all.
    Nothing else about the model changed. Commission is settled
    manually; no automated payouts."""

    name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    state = models.CharField(max_length=100, blank=True)

    referral_code = models.SlugField(max_length=50, unique=True, blank=True)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = slugify(self.name)
        super().save(*args, **kwargs)


class Coupon(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENT = "PERCENT", "Percent off"
        FIXED = "FIXED", "Fixed amount off (kobo)"

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.PositiveIntegerField(
        help_text="Percent (0-100) if PERCENT, or kobo amount if FIXED."
    )
    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Blank = unlimited.")
    times_used = models.PositiveIntegerField(default=0, editable=False)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    applies_to_courses = models.ManyToManyField(
        Course, blank=True, related_name="coupons", help_text="Empty = applies to all courses."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def clean(self):
        if self.discount_type == self.DiscountType.PERCENT and self.value > 100:
            raise ValidationError({"value": "Percent discount cannot exceed 100."})

    def save(self, *args, **kwargs):
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        ABANDONED = "ABANDONED", "Abandoned"
        REFUNDED = "REFUNDED", "Refunded"

    # PROTECT on user/course — same "never lose payment history"
    # discipline as Enrollment. A Payment is the only record of what
    # someone actually paid, kept or not.
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="payments")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="payments")
    cohort = models.ForeignKey(
        "enrollment.Cohort", on_delete=models.PROTECT, related_name="payments", null=True, blank=True
    )

    provider = models.CharField(max_length=20, default="PAYSTACK")
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    amount_kobo = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="NGN")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name="payments", null=True, blank=True)
    partner = models.ForeignKey(
        Partner, on_delete=models.PROTECT, related_name="payments", null=True, blank=True
    )

    initialized_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    raw_init_response = models.JSONField(blank=True, null=True)
    # Deviation from build spec §4's `raw_webhook_payload`: per the
    # payments addendum there is no webhook, so what's actually stored
    # is the verify-endpoint response — renamed to say what it is.
    raw_verify_response = models.JSONField(blank=True, null=True)

    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-initialized_at"]

    def __str__(self):
        return f"{self.reference} — {self.user.email} — {self.status}"


class ReconciliationFlag(TimeStampedModel):
    """Stand-in for the Phase 11 operations.Signal system, which
    doesn't exist yet. The payments addendum §2.4 requires
    sweep_paystack_transactions to raise a CRITICAL, human-reviewed
    flag for any Academy-tagged Paystack success with no matching
    local Payment — "a human looks at it," never an auto-grant. When
    Phase 11 ships, replace creation of this model with
    Signal(key="payment.reconcile_mismatch", severity=CRITICAL,
    channel=INTERRUPT) and keep this model or migrate its rows across;
    don't delete the safety net in the meantime.
    """

    reference = models.CharField(max_length=100, db_index=True)
    reason = models.CharField(max_length=255)
    raw_data = models.JSONField(blank=True, null=True)

    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolution_note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference} — {self.reason}"
