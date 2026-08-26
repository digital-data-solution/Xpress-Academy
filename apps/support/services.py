"""One choke point for creating SupportMessage rows — same discipline
as apps.engagement.services.send_email() and apps.operations
.raise_signal(). Nothing else should call SupportMessage.objects
.create() directly."""

from django.utils import timezone

from .faq import find_answer, wants_human
from .models import SupportMessage, SupportTicket


def post_learner_message(ticket: SupportTicket, body: str) -> SupportMessage:
    """Records the learner's message, then either answers it instantly
    with the FAQ bot or escalates to a human — never both, and never
    neither. Returns the learner's own message row (the bot reply, if
    any, is a separate row created here and visible in the thread)."""
    message = SupportMessage.objects.create(ticket=ticket, sender_type=SupportMessage.Sender.LEARNER, body=body)
    ticket.last_message_at = timezone.now()

    if not wants_human(body):
        match = find_answer(body)
    else:
        match = None

    if match:
        SupportMessage.objects.create(
            ticket=ticket, sender_type=SupportMessage.Sender.BOT,
            body=match.answer, matched_faq_key=match.key,
        )
        ticket.status = SupportTicket.Status.AWAITING_LEARNER
        ticket.save(update_fields=["status", "last_message_at", "updated_at"])
    else:
        _escalate(ticket, message)

    return message


ESCALATION_EMAIL_COOLDOWN_SECONDS = 60


def _escalate(ticket: SupportTicket, message: SupportMessage):
    """No FAQ entry matched (or the learner explicitly asked for a
    human) — mark the ticket as needing staff, and email ops. Reuses
    apps.operations.services._ops_recipient so this lands wherever
    OPS_ALERT_EMAIL points (contact@xpressdigitalanddatasolutions
    .online once that's set in Render), same as every other
    ops-facing notification in this codebase — never a second,
    separately-hardcoded address.

    Ticket/message rows are always created regardless — that's cheap,
    harmless data. What's rate-limited here is specifically the
    OUTBOUND EMAIL: send_email()'s dedupe_key is per-message (unique
    every time, deliberately, so a genuinely new question always
    reaches ops), which means nothing previously stopped a learner
    creating many rapid unmatched messages from generating a real
    email to ops for every single one. A per-user cooldown on the
    email specifically — not on creating tickets/messages — fixes the
    actual cost/abuse vector without restricting genuine rapid
    back-and-forth conversation."""
    from apps.engagement.models import EmailLog
    from apps.engagement.services import send_email
    from apps.operations.services import _ops_recipient

    if ticket.escalated_at is None:
        ticket.escalated_at = timezone.now()
    ticket.status = SupportTicket.Status.AWAITING_STAFF
    ticket.save(update_fields=["status", "escalated_at", "last_message_at", "updated_at"])

    recipient = _ops_recipient(ticket.organization)
    if not recipient:
        return  # nowhere to send — see _ops_recipient's own fallback chain

    cutoff = timezone.now() - timezone.timedelta(seconds=ESCALATION_EMAIL_COOLDOWN_SECONDS)
    recently_escalated = EmailLog.objects.filter(
        user=ticket.user, template_key="support_escalation", created_at__gte=cutoff,
    ).exists()
    if recently_escalated:
        return  # already notified ops about this learner very recently — ticket/message still recorded above

    from django.conf import settings
    from django.urls import reverse

    review_path = reverse(f"admin:{ticket._meta.app_label}_{ticket._meta.model_name}_change", args=[ticket.pk])
    send_email(
        to_email=recipient,
        template_key="support_escalation",
        subject=f"[Support] {ticket.subject} — {ticket.user.email}",
        html=(
            f"<p><strong>{ticket.user.email}</strong> needs a reply on a support ticket "
            f"the bot couldn't answer.</p><p>{message.body}</p>"
            f'<p><a href="{settings.SITE_URL}{review_path}">Reply in the admin</a></p>'
        ),
        user=ticket.user,
        dedupe_key=f"support_escalation:{message.id}",
    )


def notify_learner_of_staff_reply(message: SupportMessage):
    """Called from the admin the moment a staff member saves a new
    reply — closes the loop back to the learner by email, same
    send_email() pipeline as everything else. The learner also sees
    the reply next time they open the thread in-app; this is the
    "you don't have to keep checking" half of that."""
    from django.conf import settings
    from django.urls import reverse

    from apps.engagement.services import send_email

    ticket = message.ticket
    thread_path = reverse("support:thread", args=[ticket.pk])
    send_email(
        to_email=ticket.user.email,
        template_key="support_staff_reply",
        subject=f"Re: {ticket.subject} — Xpress Digital Academy support",
        html=(
            f"<p>You have a reply on your support ticket \"{ticket.subject}\":</p>"
            f"<blockquote>{message.body}</blockquote>"
            f'<p><a href="{settings.SITE_URL}{thread_path}">View and reply</a></p>'
        ),
        user=ticket.user,
        dedupe_key=f"support_staff_reply:{message.id}",
    )
