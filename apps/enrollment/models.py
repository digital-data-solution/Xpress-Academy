from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.models import Course, Lesson
from apps.common.models import TimeStampedModel


class Cohort(TimeStampedModel):
    """An optional scheduling/capacity grouping within a Course — e.g.
    a founding cohort with a start/end date and a seat cap. Not every
    enrollment belongs to one (Enrollment.cohort is nullable)."""

    # PROTECT: a cohort carries dates/capacity/founding-status that
    # matter for reporting even after a course is restructured —
    # same "don't lose it to a careless delete" discipline as
    # Organization and Course→Enrollment.
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="cohorts")
    name = models.CharField(max_length=255)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField(null=True, blank=True)
    is_founding = models.BooleanField(default=False)

    class Meta:
        ordering = ["-starts_at"]

    def __str__(self):
        return f"{self.course.title} — {self.name}"


class Enrollment(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRED = "EXPIRED", "Expired"
        REVOKED = "REVOKED", "Revoked"
        COMPLETED = "COMPLETED", "Completed"

    class Source(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        MANUAL = "MANUAL", "Manual"
        COUPON = "COUPON", "Coupon"
        CLINIC_PARTNER = "CLINIC_PARTNER", "Clinic partner"

    # PROTECT on both — per build spec §10, enrollment records must
    # never be lost to a careless admin delete of the course, and the
    # same protection is extended here to the user for the same
    # reason (it's the only record of what someone paid for).
    user = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="enrollments")
    cohort = models.ForeignKey(
        Cohort, on_delete=models.PROTECT, related_name="enrollments", null=True, blank=True
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.MANUAL)

    # partner_clinic FK is added in Phase 6 alongside apps.payments.PartnerClinic
    # (that model doesn't exist yet). The CLINIC_PARTNER source choice
    # is already here so Source values don't need a later migration.

    content_version_at_enrollment = models.PositiveIntegerField(
        editable=False,
        help_text="Snapshot of Course.content_version at enrollment time — set automatically, not admin-editable.",
    )

    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Null = lifetime access.")
    completed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "course"], name="unique_user_course_enrollment"),
        ]
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.email} — {self.course.title} ({self.status})"

    def save(self, *args, **kwargs):
        # Snapshot on first save only — an existing enrollment's
        # version must never silently track a later content_version
        # bump on the course (that's the whole point of the field).
        if self._state.adding and self.course_id:
            self.content_version_at_enrollment = self.course.content_version
        super().save(*args, **kwargs)


class LessonProgress(TimeStampedModel):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="lesson_progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_entries")

    watched_seconds = models.PositiveIntegerField(default=0)
    furthest_second = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "lesson"], name="unique_enrollment_lesson_progress"),
        ]

    def __str__(self):
        return f"{self.enrollment.user.email} — {self.lesson.title}"

    def clean(self):
        if self.lesson.module.course_id != self.enrollment.course_id:
            raise ValidationError("Lesson does not belong to the enrollment's course.")
