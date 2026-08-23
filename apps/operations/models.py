"""Phase 11 — build spec: "The system's job is to tell Sam what needs
a decision today, recommend what to do, and let everything else stay
quiet." Alert fatigue is the failure mode this whole app is designed
against, not missed events — see services.py and tasks.py for how
that principle actually gets enforced (interrupt cap, dedup, the
quiet-day digest line).
"""

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q

from apps.common.models import TimeStampedModel, OrganizationOwnedModel


class SignalRule(models.Model):
    """Thresholds live here (threshold_config), not in code — build
    spec: "you'll be tuning completion-rate floors and refund
    ceilings constantly for six months. If changing a number needs a
    deploy, the numbers stay wrong." Seeded with sensible defaults via
    a data migration; edit in admin from then on."""

    class Channel(models.TextChoices):
        DIGEST = "DIGEST", "Daily digest"
        INTERRUPT = "INTERRUPT", "Immediate interrupt"

    key = models.SlugField(max_length=100, unique=True)
    category = models.CharField(max_length=20)  # Signal.Category values, not FK — rules can predate any Signal
    default_severity = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    threshold_config = models.JSONField(default=dict, blank=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.DIGEST)
    cooldown_days = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "key"]

    def __str__(self):
        return self.key


class Signal(OrganizationOwnedModel):
    class Category(models.TextChoices):
        MONEY = "MONEY", "Money"
        QUALITY = "QUALITY", "Quality"
        LEARNER = "LEARNER", "Learner"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"
        PARTNER = "PARTNER", "Partner"
        SYSTEM = "SYSTEM", "System"
        LEGAL = "LEGAL", "Legal"
        GROWTH = "GROWTH", "Growth"

    class Severity(models.TextChoices):
        INFO = "INFO", "Info"
        ATTENTION = "ATTENTION", "Attention"
        URGENT = "URGENT", "Urgent"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        SNOOZED = "SNOOZED", "Snoozed"
        RESOLVED = "RESOLVED", "Resolved"
        DISMISSED = "DISMISSED", "Dismissed"

    key = models.SlugField(max_length=100)
    category = models.CharField(max_length=20, choices=Category.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices)

    title = models.CharField(max_length=255)
    detail = models.TextField(blank=True)
    recommended_action = models.TextField(blank=True)
    action_url = models.CharField(max_length=500, blank=True)

    # The Course/Payment/Enrollment/etc this signal is about. Generic
    # because the subject varies wildly by category and a per-category
    # FK set would mean a new nullable column every time a new rule
    # touches a new model.
    subject_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    subject_id = models.PositiveIntegerField(null=True, blank=True)
    subject = GenericForeignKey("subject_type", "subject_id")

    # Unique only among NOT-resolved-or-dismissed signals — a course
    # that was fixed and later regresses must be able to raise the
    # same dedupe_key again as a fresh signal. Enforced at the DB
    # level via a partial unique index, not just application logic.
    dedupe_key = models.CharField(max_length=255)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    snoozed_until = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    dismissal_reason = models.CharField(max_length=255, blank=True)

    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)
    occurrence_count = models.PositiveIntegerField(default=1)

    decision_due = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-severity", "-last_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["dedupe_key"],
                condition=~Q(status__in=["RESOLVED", "DISMISSED"]),
                name="unique_open_signal_dedupe_key",
            ),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class CalendarObligation(OrganizationOwnedModel):
    """The deadline register — CAC returns, trademark renewal, SSL/
    domain expiry, instructor agreement renewals, school contract
    renewals, content review dates, JAMB/WAEC windows, TRCN/VCN
    cycles. Anything with a date that costs money or standing if
    missed. Seeded in admin; legal.obligation_due surfaces it as the
    lead window opens."""

    class ObligationType(models.TextChoices):
        REGULATORY = "REGULATORY", "Regulatory"
        CONTRACTUAL = "CONTRACTUAL", "Contractual"
        OPERATIONAL = "OPERATIONAL", "Operational"
        RENEWAL = "RENEWAL", "Renewal"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        DONE = "DONE", "Done"
        OVERDUE = "OVERDUE", "Overdue"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    obligation_type = models.CharField(max_length=20, choices=ObligationType.choices)
    due_date = models.DateField()
    lead_days = models.PositiveIntegerField(default=30, help_text="How far ahead to start warning.")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="obligations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    recurrence_rule = models.CharField(
        max_length=100, blank=True, help_text="e.g. 'yearly', 'quarterly' — informational for now, not auto-applied."
    )
    notes = models.TextField(blank=True)
    evidence_document = models.FileField(upload_to="obligations/", blank=True, null=True)

    class Meta:
        ordering = ["due_date"]

    def __str__(self):
        return f"{self.title} — due {self.due_date}"


class DigestRun(TimeStampedModel):
    """Kept in full so "why didn't I know about this" always has a
    retrievable answer — build spec §1."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="digest_runs")
    run_date = models.DateField()
    sent_at = models.DateTimeField(null=True, blank=True)
    signal_count = models.PositiveIntegerField(default=0)
    email_log = models.ForeignKey(
        "engagement.EmailLog", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    rendered_html = models.TextField(blank=True)

    class Meta:
        ordering = ["-run_date"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "run_date"], name="unique_digest_per_day"),
        ]

    def __str__(self):
        return f"Digest {self.run_date}"


class InterruptBudget(models.Model):
    """The actual gate for the 3-per-day cap — one row per
    (organization, date), incremented under select_for_update() so
    concurrent Celery workers raising CRITICAL signals at the same
    moment can never together exceed the cap. Same atomic-counter
    pattern as apps.certificates.services.next_serial(); a plain
    check-then-create on InterruptLog alone is racy under real
    concurrency, not just a test artifact — see
    apps.operations.services.maybe_send_interrupt."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="interrupt_budgets")
    date = models.DateField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "date"], name="unique_interrupt_budget_per_day"),
        ]


class InterruptLog(TimeStampedModel):
    """The audit trail — keeping the actual rows means "what were
    today's 3" is answerable, same reasoning as DigestRun keeping
    rendered_html. InterruptBudget above is what actually enforces
    the cap; this is just the record of what went out."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="interrupt_logs")
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE, related_name="interrupt_logs")
    sent_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
