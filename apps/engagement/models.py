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
