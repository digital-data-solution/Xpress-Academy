"""Learner support — a normal Django-backed inbox rather than a
separate Supabase Realtime chat widget. The reasoning (asked for
explicitly): Supabase's client-side chat feature needs its own
identity/auth wiring alongside Django's, so it would end up as a
second, duplicate notion of "who is this user" living next to the one
that already exists here. This app just stores conversations in the
same Postgres database (which happens to already be hosted on
Supabase — so nothing about the data's *location* changes), and reuses
the same login, admin, and email pipeline as everything else in the
codebase. Same one-choke-point discipline as apps.engagement.services
.send_email() and apps.operations — a message always goes through
services.py, never created ad hoc from a view or the admin.
"""

from django.conf import settings
from django.db import models

from apps.common.models import OrganizationOwnedModel, TimeStampedModel


class SupportTicket(OrganizationOwnedModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        AWAITING_STAFF = "AWAITING_STAFF", "Awaiting staff reply"
        AWAITING_LEARNER = "AWAITING_LEARNER", "Awaiting learner reply"
        RESOLVED = "RESOLVED", "Resolved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    # Set the moment a message first needs a human — never cleared, so
    # it stays a true record of "did this ever need a person" even
    # after resolution, distinct from status which does change.
    escalated_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        return f"{self.subject} — {self.user.email} ({self.status})"


class SupportMessage(TimeStampedModel):
    class Sender(models.TextChoices):
        LEARNER = "LEARNER", "Learner"
        BOT = "BOT", "Bot"
        STAFF = "STAFF", "Staff"

    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name="messages")
    sender_type = models.CharField(max_length=20, choices=Sender.choices)
    # Only set for STAFF messages, and only when a human actually typed
    # this one — lets the thread show who answered without guessing.
    staff_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    body = models.TextField()
    # Which FAQ entry the bot matched, if any — kept so a human
    # reviewing the thread later can see why the bot said what it
    # said, and so a poorly-matching FAQ entry can be found and fixed.
    matched_faq_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.ticket_id} — {self.sender_type} — {self.created_at:%Y-%m-%d %H:%M}"
