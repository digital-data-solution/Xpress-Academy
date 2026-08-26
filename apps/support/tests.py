from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.engagement.models import EmailLog
from apps.organizations.models import Organization

from .faq import find_answer, wants_human
from .models import SupportMessage, SupportTicket
from .services import notify_learner_of_staff_reply, post_learner_message


class FAQMatchingTests(TestCase):
    def test_matches_payment_question(self):
        entry = find_answer("I was debited but the payment still shows pending")
        self.assertEqual(entry.key, "payment_pending")

    def test_no_match_returns_none(self):
        self.assertIsNone(find_answer("xyz completely unrelated gibberish 12345"))

    def test_wants_human_detects_explicit_request(self):
        self.assertTrue(wants_human("I want to talk to a real person please"))
        self.assertFalse(wants_human("how do I download my certificate"))


class SupportServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Xpress Digital Academy")
        self.user = User.objects.create_user(email="learner@example.com", password="pw12345!")
        self.ticket = SupportTicket.objects.create(organization=self.org, user=self.user, subject="Help")

    def test_faq_match_answers_instantly_without_escalating(self):
        post_learner_message(self.ticket, "my password reset email never arrived")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SupportTicket.Status.AWAITING_LEARNER)
        self.assertIsNone(self.ticket.escalated_at)
        bot_reply = self.ticket.messages.filter(sender_type=SupportMessage.Sender.BOT).first()
        self.assertIsNotNone(bot_reply)

    def test_unmatched_message_escalates_and_emails_ops(self):
        with self.settings(OPS_ALERT_EMAIL="ops@example.com"):
            post_learner_message(self.ticket, "completely unrelated gibberish question 12345")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SupportTicket.Status.AWAITING_STAFF)
        self.assertIsNotNone(self.ticket.escalated_at)
        self.assertFalse(self.ticket.messages.filter(sender_type=SupportMessage.Sender.BOT).exists())
        log = EmailLog.objects.filter(template_key="support_escalation").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.to_email, "ops@example.com")

    def test_explicit_human_request_escalates_even_with_faq_keywords_present(self):
        with self.settings(OPS_ALERT_EMAIL="ops@example.com"):
            post_learner_message(self.ticket, "I want a real person, forget the password reset bot answer")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, SupportTicket.Status.AWAITING_STAFF)

    def test_staff_reply_emails_learner(self):
        message = SupportMessage.objects.create(
            ticket=self.ticket, sender_type=SupportMessage.Sender.STAFF, body="We've checked — you're all set.",
        )
        notify_learner_of_staff_reply(message)
        log = EmailLog.objects.filter(template_key="support_staff_reply").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.to_email, self.user.email)

    def test_rapid_unmatched_messages_only_email_ops_once(self):
        """The real risk this closes: send_email()'s dedupe_key here
        is per-message (deliberately unique every time, so a genuinely
        new question always reaches ops) — nothing previously stopped
        a learner rapidly creating many unmatched messages from
        generating a real email to ops for every single one. Ticket/
        message rows still get created each time; only the repeated
        outbound email is suppressed."""
        with self.settings(OPS_ALERT_EMAIL="ops@example.com"):
            for i in range(5):
                post_learner_message(self.ticket, f"unrelated gibberish {i} 12345")
        self.assertEqual(
            SupportMessage.objects.filter(ticket=self.ticket, sender_type=SupportMessage.Sender.LEARNER).count(), 5,
        )
        self.assertEqual(EmailLog.objects.filter(template_key="support_escalation").count(), 1)


class SupportViewTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(name="Xpress Digital Academy")
        self.user = User.objects.create_user(email="learner2@example.com", password="pw12345!")
        self.client.force_login(self.user)

    def test_creating_a_ticket_gets_a_bot_answer_on_the_thread_page(self):
        response = self.client.post(reverse("support:inbox"), {
            "subject": "Can't log in",
            "body": "I forgot my password and can't log in",
        }, follow=True)
        self.assertContains(response, "Forgot password")

    def test_learner_cannot_view_another_learners_ticket(self):
        other = User.objects.create_user(email="other@example.com", password="pw12345!")
        ticket = SupportTicket.objects.create(organization=self.org, user=other, subject="Private")
        response = self.client.get(reverse("support:thread", args=[ticket.pk]))
        self.assertEqual(response.status_code, 404)
