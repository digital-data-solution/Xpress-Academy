"""Phase 10 — instructor marketplace platform. Built per the owner's
explicit override of the spec's original "wait for a first sale" gate
(see README's *What's next*). HARD STOP 3 from the spec is still
honoured though, independent of that override, because it's a sound
software-sequencing reason on its own: the earnings ledger (EarningsEntry/
Payout, bottom of this file) must not exist as a live money-moving
path before the review workflow and publication gate are complete and
tested — money flowing before quality control creates an incentive to
publish before the gate is trustworthy, which is a real problem the
code itself should prevent, not just a launch-timing concern.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.models import OrganizationOwnedModel, TimeStampedModel


class Vertical(OrganizationOwnedModel):
    """Build spec §4.1: "No vertical opens without a named domain
    reviewer." A Course belongs to one; review_status can never reach
    APPROVED if the Vertical has no domain_reviewer — enforced in
    Course.clean(), not just documented."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_open_for_applications = models.BooleanField(default=False)
    domain_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    reviewer_credentials_note = models.TextField(blank=True)
    # §4.3 — clinical/legal/financial/exam-outcome/offensive-security
    # verticals route to legal review before approval, not just staff review.
    requires_legal_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Instructor(OrganizationOwnedModel):
    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "UNVERIFIED", "Unverified"
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    class Status(models.TextChoices):
        APPLICANT = "APPLICANT", "Applicant"
        ONBOARDING = "ONBOARDING", "Onboarding"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        OFFBOARDED = "OFFBOARDED", "Offboarded"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="instructor_profile")

    display_name = models.CharField(max_length=255)
    headline = models.CharField(max_length=255, blank=True)
    bio = CKEditor5Field(blank=True, config_name="default")
    photo = models.ImageField(upload_to="instructors/photos/", blank=True, null=True)
    credentials = models.TextField(blank=True)

    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    referral_code = models.SlugField(max_length=50, unique=True, blank=True)
    own_traffic_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("70.00"))
    platform_traffic_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("50.00"))

    payout_bank_name = models.CharField(max_length=255, blank=True)
    payout_account_number = models.CharField(max_length=20, blank=True)
    payout_account_name = models.CharField(max_length=255, blank=True)

    agreement_signed_at = models.DateTimeField(null=True, blank=True)
    agreement_version = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLICANT)
    suspended_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if not self.referral_code:
            base = slugify(self.display_name) or "instructor"
            code = base
            n = 2
            while Instructor.objects.filter(referral_code=code).exclude(pk=self.pk).exists():
                code = f"{base}-{n}"
                n += 1
            self.referral_code = code
        super().save(*args, **kwargs)

    @property
    def is_eligible_for_courses(self) -> bool:
        """§2: "An Instructor cannot be attached to a Course unless
        verification_status == VERIFIED and agreement_signed_at is
        set." The actual enforcement is on Course.clean() below —
        this property is what that check calls, kept here so the
        rule lives with the model it's about."""
        return self.verification_status == self.VerificationStatus.VERIFIED and self.agreement_signed_at is not None


class InstructorDocument(TimeStampedModel):
    """Credential evidence — licence, degree, certification. Admin-only
    visibility, never exposed on any public or /teach/ page."""

    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name="credential_documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="instructors/documents/")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.instructor.display_name} — {self.title}"


class CourseReview(TimeStampedModel):
    """Append-only — a second review round creates a new row, never
    overwrites the first. Build spec §4.2: Part A (Sam/staff, quality
    and safety) and Part B (domain reviewer, accuracy) are both
    represented in `checklist`; `outcome` is the round's final verdict."""

    class Outcome(models.TextChoices):
        APPROVED = "APPROVED", "Approved"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes requested"
        REJECTED = "REJECTED", "Rejected"

    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    round = models.PositiveIntegerField()

    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    outcome = models.CharField(max_length=20, choices=Outcome.choices, blank=True)
    checklist = models.JSONField(default=dict, blank=True)
    notes_to_instructor = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)  # staff only — never shown on /teach/

    class Meta:
        ordering = ["course", "-round"]
        constraints = [
            models.UniqueConstraint(fields=["course", "round"], name="unique_course_review_round"),
        ]

    def __str__(self):
        return f"{self.course.title} — round {self.round} ({self.outcome or 'in progress'})"


class EarningsEntry(TimeStampedModel):
    """Append-only ledger — mirrors the LedgerEntry pattern from
    AjoApp, no mutable balance field anywhere. Balance is always
    SUM(amount_kobo), computed on demand by get_instructor_balance()
    in services.py, never stored. HARD STOP 3: this model exists in
    the schema but the code path that writes real money-moving rows
    (grant_access, once wired) must not go live before the publication
    gate is proven — see the module docstring."""

    class EntryType(models.TextChoices):
        SALE_GROSS = "SALE_GROSS", "Sale (gross)"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform fee"
        INSTRUCTOR_EARNING = "INSTRUCTOR_EARNING", "Instructor earning"
        REFUND_REVERSAL = "REFUND_REVERSAL", "Refund reversal"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        PAYOUT_SENT = "PAYOUT_SENT", "Payout sent"

    class Attribution(models.TextChoices):
        OWN_TRAFFIC = "OWN_TRAFFIC", "Own traffic"
        PLATFORM_TRAFFIC = "PLATFORM_TRAFFIC", "Platform traffic"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="earnings_entries")
    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="earnings_entries")
    course = models.ForeignKey("catalog.Course", on_delete=models.PROTECT, related_name="earnings_entries", null=True, blank=True)
    payment = models.ForeignKey("payments.Payment", on_delete=models.PROTECT, related_name="earnings_entries", null=True, blank=True)
    payout = models.ForeignKey("Payout", on_delete=models.PROTECT, related_name="entries", null=True, blank=True)

    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    amount_kobo = models.IntegerField(help_text="Signed — credits positive, debits negative.")
    attribution = models.CharField(max_length=20, choices=Attribution.choices, blank=True)
    # Snapshot, never recalculated — same discipline as
    # certificate serials and payment amounts elsewhere in this codebase.
    rate_applied = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.instructor.display_name} — {self.entry_type} — {self.amount_kobo}"


class Payout(TimeStampedModel):
    """Manual only — build spec §2: "Generate the statement, Sam
    reviews, Sam pays by bank transfer, Sam marks it sent with the
    reference." No automated transfers or Paystack subaccount splits."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        APPROVED = "APPROVED", "Approved"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    instructor = models.ForeignKey(Instructor, on_delete=models.PROTECT, related_name="payouts")
    period_start = models.DateField()
    period_end = models.DateField()
    gross_kobo = models.PositiveIntegerField(default=0)
    amount_kobo = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    bank_reference = models.CharField(max_length=255, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    statement_pdf = models.FileField(upload_to="instructors/payouts/", blank=True, null=True)

    class Meta:
        ordering = ["-period_end"]

    def __str__(self):
        return f"{self.instructor.display_name} — {self.period_start} to {self.period_end} ({self.status})"


class CourseHealth(models.Model):
    """Computed nightly, stored for trend — build spec §4.4."""

    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="health_snapshots")
    date = models.DateField()
    enrollments_30d = models.PositiveIntegerField(default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    refund_rate_30d = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    complaint_count_30d = models.PositiveIntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    instructor_response_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    days_since_content_review = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["course", "date"], name="unique_course_health_per_day"),
        ]

    def __str__(self):
        return f"{self.course.title} — {self.date}"


class CourseRating(TimeStampedModel):
    """§4.5: only enrolled learners past 50% progress may rate.
    Instructors may respond publicly once per review, never edit or
    delete. Sam can remove a review only for abuse, logged."""

    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="course_ratings")
    rating = models.PositiveSmallIntegerField()
    review_text = models.TextField(blank=True)
    instructor_response = models.TextField(blank=True)
    instructor_responded_at = models.DateTimeField(null=True, blank=True)
    is_removed = models.BooleanField(default=False)
    removal_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["course", "user"], name="unique_rating_per_learner_per_course"),
        ]

    def __str__(self):
        return f"{self.course.title} — {self.rating}★ by {self.user.email}"

    def clean(self):
        if not (1 <= self.rating <= 5):
            raise ValidationError({"rating": "Must be between 1 and 5."})


class LearnerInstructorMessage(TimeStampedModel):
    """§4.7 anti-poaching: "All learner-instructor messaging runs
    through the platform, logged." Never a substitute for learner
    support — this is instructor Q&A, logged so it can't quietly move
    to WhatsApp."""

    class Sender(models.TextChoices):
        LEARNER = "LEARNER", "Learner"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"

    course = models.ForeignKey("catalog.Course", on_delete=models.CASCADE, related_name="learner_messages")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    sender = models.CharField(max_length=20, choices=Sender.choices)
    body = models.TextField()

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.course.title} — {self.sender} — {self.created_at:%Y-%m-%d}"
