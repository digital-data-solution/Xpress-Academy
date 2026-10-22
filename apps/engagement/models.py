import re

from django.db import models

from apps.catalog.models import Course, Lesson
from apps.common.models import TimeStampedModel


class EmailLog(TimeStampedModel):
    """Every outbound email goes through send_email() in services.py,
    which writes exactly one of these per attempt — this table is the
    audit trail and the dedupe mechanism at once (see dedupe_key)."""

    class Status(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    # SET_NULL, not PROTECT: this is a log, not a record of value like
    # Payment/Enrollment. Losing the user link on an old log row if an
    # account is ever hard-deleted is fine; the log entry itself still
    # has to_email for reference.
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="email_logs"
    )
    to_email = models.EmailField()
    template_key = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    provider_id = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # The idempotency key — send_email() checks this before doing
    # anything, so a retried Celery task (or two tasks racing on the
    # same event) can never double-send. Null allowed for anything
    # that's fine to send more than once (rare — most calls pass one).
    dedupe_key = models.CharField(max_length=255, unique=True, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.template_key} → {self.to_email} ({self.status})"


class Lead(TimeStampedModel):
    """An anonymous site visitor's email, captured before they're
    ready to create a full account — the gap identified after
    checking the Growth dashboard: diagnostics and quiz-builder both
    capture leads from people already engaging with specific content,
    but someone just browsing the course catalog or landing page had
    no way to leave contact info at all. Deliberately its own
    lightweight model, not a User: signup requires a password and
    creates real platform access, which is exactly the commitment a
    footer email-capture widget should NOT require."""

    email = models.EmailField(unique=True)
    source = models.CharField(
        max_length=100, blank=True,
        help_text="Where this lead was captured, e.g. 'footer', 'catalog' — free text, not a choice list, "
                   "so a new capture point never needs a migration to add its own label.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class LiveSession(TimeStampedModel):
    # PROTECT: scheduling data (date, join link) with real business
    # value, same discipline as Cohort — see apps.enrollment.models.
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="live_sessions")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    join_url = models.URLField(blank=True)
    recording_lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="live_session_recordings"
    )
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return f"{self.course.title} — {self.title} ({self.starts_at:%Y-%m-%d %H:%M})"


OFFICE_NAME_RE = re.compile(
    r"\b(directorate|department|dept|division|unit|office|ministry|agency|commission|secretariat|"
    r"inspection|headquarters|hq|zonal|laboratory|lab)\b", re.IGNORECASE,
)


class SelarContact(TimeStampedModel):
    """Someone who touched one of our Selar products (free sample
    download, abandoned checkout, or paid purchase). Selar has no
    webhooks on the free plan, so these arrive by import — see the
    import_selar_contacts command and apps.engagement.selar for the
    follow-up sequence they drive. Its own model rather than Lead:
    a Lead has no name and no notion of where in the funnel someone
    stopped, and both matter for the follow-up copy."""

    class Status(models.TextChoices):
        FREE = "FREE", "Downloaded free sample"
        ABANDONED = "ABANDONED", "Abandoned paid checkout"
        PAID = "PAID", "Paid"

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices)
    # When the contact entered their current status — the follow-up
    # schedule counts days from here, not from created_at, so someone
    # who downloads the free sample and abandons checkout a week later
    # starts the abandoned-cart sequence fresh.
    status_changed_at = models.DateTimeField()
    unsubscribed = models.BooleanField(
        default=False, help_text="Tick when someone replies asking to stop — no further follow-ups are sent.",
    )
    # Selar order reference (e.g. S466KF16168BX). Set by a buyer on the
    # activation page, which grants video access immediately; confirmed
    # when the same reference shows up in an imported Selar sales export.
    # One reference unlocks one account, so a shared reference is useless.
    reference = models.CharField(max_length=20, blank=True, db_index=True)
    reference_verified = models.BooleanField(
        default=False,
        help_text="True once this reference appears in a real Selar sales export. "
                  "Unverified claims older than a few days are reported by import_selar_contacts.",
    )

    class Meta:
        ordering = ["-status_changed_at"]

    def __str__(self):
        return f"{self.email} ({self.status})"

    @property
    def is_office(self):
        """A shared office account (e.g. "PORTS INSPECTION DIRECTORATE
        YABA-LAGOS") rather than a person — gets a team-focused offer."""
        return bool(OFFICE_NAME_RE.search(self.name))

    @property
    def first_name(self):
        # No personal name (blank, or an office account) -> "Dear
        # Sir/Ma", the respectful default for a Nigerian professional
        # audience.
        if self.is_office or not self.name.strip():
            return "Sir/Ma"
        return self.name.split()[0].title()
