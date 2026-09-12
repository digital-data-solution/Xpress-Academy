"""Institutional licensing — build spec §B: schools as a billable
entity, N student seats, term-based, bulk CSV enrolment.

Deliberately reuses the existing Enrollment engine rather than
inventing a parallel one: an institutionally-enrolled student is a
normal enrollment.Enrollment row (source=INSTITUTIONAL,
institutional_license set), so everything downstream — course access,
progress, quizzes, certificates — already works with zero new code.
See apps.enrollment.models.Enrollment.

Paystack invoicing is deliberately NOT built here yet — the build
spec's own constraint is explicit: "Ask me before changing anything
in the Paystack path." Institution/InstitutionalLicense carry the
fields a later invoicing step will need (amount_kobo, paid_at) in the
same shape as payments.Payment, so that work is additive when it
comes, not a redesign.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.catalog.models import Course
from apps.common.models import OrganizationOwnedModel, TimeStampedModel, UUIDModel


class Institution(OrganizationOwnedModel):
    """A school/proprietor as a billable customer — distinct from
    organizations.Organization (the platform tenant itself; today
    there's exactly one row, Xpress Digital Academy). An Institution
    is a *customer* of that tenant, not a tenant itself."""

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    # PROTECT: same "never lose the paying customer's record to a
    # careless delete" discipline as Enrollment/Payment.
    proprietor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="institutions_owned",
        help_text="The proprietor's own login — will see the per-school dashboard.",
    )
    contact_phone = models.CharField(max_length=32, blank=True)
    state = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class InstitutionalLicense(TimeStampedModel):
    """One term-based purchase: N seats across a set of courses,
    valid term_starts_at -> term_ends_at. The seat cap and course
    grant are enforced by services.bulk_enroll_students_from_csv, not
    by this model alone — real enrollment.Enrollment rows (via the
    reverse `enrollments` relation) are the actual source of truth for
    who's using a seat, same "snapshot / actual records win" discipline
    as the rest of this platform."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending — not yet paid"
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        CANCELED = "CANCELED", "Canceled"

    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="licenses")
    courses = models.ManyToManyField(
        Course, related_name="institutional_licenses",
        help_text="Which course(s) this licence's seats grant access to.",
    )

    seats = models.PositiveIntegerField(help_text="Total student seats this licence covers.")
    term_starts_at = models.DateTimeField()
    term_ends_at = models.DateTimeField(help_text="Enrollments created under this licence expire here.")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    # Paystack invoicing isn't wired up yet (see module docstring) —
    # these fields exist now so that step is additive later, in the
    # same shape as payments.Payment.amount_kobo/paid_at, for reuse of
    # the same reconciliation patterns when it's built.
    amount_kobo = models.PositiveIntegerField(
        null=True, blank=True, help_text="Quoted price in kobo, once agreed with the proprietor."
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-term_starts_at"]

    def __str__(self):
        return (
            f"{self.institution.name} — {self.seats} seats "
            f"({self.term_starts_at:%Y-%m-%d}–{self.term_ends_at:%Y-%m-%d})"
        )

    def clean(self):
        if self.term_ends_at and self.term_starts_at and self.term_ends_at <= self.term_starts_at:
            raise ValidationError({"term_ends_at": "Must be after term_starts_at."})

    @property
    def seats_used(self) -> int:
        return self.enrollments.exclude(status="REVOKED").count()

    @property
    def seats_remaining(self) -> int:
        return max(0, self.seats - self.seats_used)

    @property
    def is_full(self) -> bool:
        return self.seats_remaining <= 0


class DiagnosticMockTest(OrganizationOwnedModel):
    """A free, shareable diagnostic mock exam — build spec §B's "door-
    opener for outbound." Deliberately NOT built on assessment.Quiz /
    Attempt: those assume an enrolled, paying learner
    (Attempt.enrollment is a required FK) but a diagnostic test-taker
    is, by definition, someone who hasn't bought anything yet — that's
    the whole point of a diagnostic. This reuses the real
    Question/Choice/SyllabusTopic *data* (same is_publishable gating
    as every other quiz pool, via services._build_diagnostic_snapshot)
    without any of the course/enrollment plumbing that data doesn't
    need here."""

    institution = models.ForeignKey(
        "licensing.Institution", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="diagnostic_tests",
        help_text="Optional — set when this link was made for one prospect school, so their "
                   "proprietor gets a school-level summary filtered to just their students. "
                   "Blank = a general public diagnostic, shareable with anyone.",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    bank = models.ForeignKey(
        "assessment.QuestionBank", on_delete=models.PROTECT, related_name="diagnostic_tests"
    )
    syllabus_topic_filter = models.ManyToManyField(
        "assessment.SyllabusTopic", blank=True, related_name="diagnostic_tests",
        help_text="Blank = pull from the whole bank.",
    )
    question_count = models.PositiveIntegerField(default=20)
    time_limit_minutes = models.PositiveIntegerField(default=30, help_text="0 = no time limit.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class DiagnosticAttempt(TimeStampedModel, UUIDModel):
    """One prospective student's run through a DiagnosticMockTest.
    Identified publicly by `uuid` (see UUIDModel), never by the
    sequential `id` — same "must never leak sequential information"
    reasoning UUIDModel itself is built for (certificate verification
    was the original case; a public, unauthenticated diagnostic-result
    URL is exactly the same shape of problem)."""

    test = models.ForeignKey(DiagnosticMockTest, on_delete=models.CASCADE, related_name="attempts")

    student_name = models.CharField(max_length=255)
    student_email = models.EmailField(blank=True)
    # Free text, not a FK to Institution: a diagnostic taker is
    # frequently not yet a student at any institution row we have —
    # that's the entire premise of a door-opener. The school-level
    # summary groups by this field (or by test.institution when set).
    school_name = models.CharField(max_length=255, blank=True)

    question_snapshot = models.JSONField(default=list)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    score_percent = models.PositiveIntegerField(null=True, blank=True)
    # {"Ecology": {"correct": 3, "total": 5}, ...} — computed once at
    # finalize time from the snapshot + answers, same "snapshot is
    # authoritative, never re-derive from a live query later"
    # discipline as assessment.Attempt. Drives both the per-student
    # report and the school-level rollup without re-joining anything.
    topic_breakdown = models.JSONField(default=dict, blank=True)

    report_pdf = models.FileField(upload_to="diagnostic_reports/", blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        status = f"{self.score_percent}%" if self.score_percent is not None else "in progress"
        return f"{self.student_name} — {self.test.title} ({status})"

    @property
    def is_in_progress(self) -> bool:
        return self.submitted_at is None

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at) and self.is_in_progress and timezone.now() > self.expires_at


class DiagnosticAnswer(models.Model):
    """Deliberately simpler than assessment.AttemptAnswer: choice ids
    are graded against the ones embedded in the attempt's own
    question_snapshot (already the authoritative set for that attempt)
    rather than validated against a live Choice FK — there's no extra
    trust to establish, a tampered id simply can't match a correct_id
    that isn't in the snapshot, so a defensive live-FK check would add
    nothing here."""

    attempt = models.ForeignKey(DiagnosticAttempt, on_delete=models.CASCADE, related_name="answers")
    question_id = models.PositiveIntegerField()
    selected_choice_ids = models.JSONField(default=list)
    is_correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question_id"], name="unique_diagnostic_attempt_question"),
        ]

    def __str__(self):
        return f"{self.attempt_id} — Q{self.question_id} — {'correct' if self.is_correct else 'incorrect'}"
