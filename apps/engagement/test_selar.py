"""The Selar follow-up sequence emails real prospects from the
company address, so the things that would embarrass us are tested
here: double-sends, emailing someone who already paid, dragging a
buyer back into the sales sequence on re-import, and a late import
dumping the whole backlog on someone at once."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Audience, Course, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

from .models import EmailLog, SelarContact
from .selar import record_contact, send_selar_followups


@pytest.fixture(autouse=True)
def _no_real_email(settings):
    settings.RESEND_API_KEY = ""
    settings.EMAIL_HOST_USER = ""
    settings.EMAIL_HOST_PASSWORD = ""


@pytest.fixture
def psr_course():
    org = Organization.objects.create(name="Test Org", from_email="test@example.com")
    programme = Programme.objects.create(organization=org, title="Civil Service", audience=Audience.BREEDER)
    return Course.objects.create(
        organization=org, programme=programme, title="Public Service Rules Guide",
        slug="public-service-rules-guide", audience=Audience.BREEDER,
    )


def keys():
    return set(EmailLog.objects.values_list("dedupe_key", flat=True))


@pytest.mark.django_db
class TestSequence:
    def test_free_contact_gets_nothing_before_day_two(self):
        record_contact(email="a@x.com", name="Ada Obi", status=SelarContact.Status.FREE)
        assert send_selar_followups() == {}

    def test_free_contact_score_then_offer_once_each(self):
        now = timezone.now()
        record_contact(email="a@x.com", name="Ada Obi", status=SelarContact.Status.FREE, when=now - timedelta(days=2))
        send_selar_followups(now=now)
        send_selar_followups(now=now)
        assert keys() == {"selar:free-score:a@x.com"}
        send_selar_followups(now=now + timedelta(days=3))
        assert keys() == {"selar:free-score:a@x.com", "selar:free-offer:a@x.com"}
        assert "Ada" in EmailLog.objects.get(dedupe_key="selar:free-score:a@x.com").subject

    def test_late_import_sends_only_latest_due_step(self):
        record_contact(email="a@x.com", status=SelarContact.Status.FREE, when=timezone.now() - timedelta(days=9))
        send_selar_followups()
        assert keys() == {"selar:free-offer:a@x.com"}

    def test_abandoned_contact_emailed_same_day(self):
        record_contact(email="b@x.com", name="Bayo", status=SelarContact.Status.ABANDONED)
        send_selar_followups()
        assert keys() == {"selar:abandoned-1:b@x.com"}

    def test_unsubscribed_contact_gets_nothing(self):
        c = record_contact(email="b@x.com", status=SelarContact.Status.ABANDONED)
        c.unsubscribed = True
        c.save()
        send_selar_followups()
        assert keys() == set()

    def test_status_never_moves_backwards(self):
        record_contact(email="c@x.com", status=SelarContact.Status.PAID)
        record_contact(email="C@x.com", status=SelarContact.Status.FREE)
        assert SelarContact.objects.get(email="c@x.com").status == SelarContact.Status.PAID

    def test_abandoned_after_free_restarts_clock(self):
        old = timezone.now() - timedelta(days=10)
        record_contact(email="d@x.com", status=SelarContact.Status.FREE, when=old)
        record_contact(email="d@x.com", status=SelarContact.Status.ABANDONED)
        send_selar_followups()
        assert keys() == {"selar:abandoned-1:d@x.com"}


@pytest.mark.django_db
class TestBuyers:
    def test_paid_contact_gets_account_enrollment_and_one_welcome(self, psr_course, django_capture_on_commit_callbacks):
        record_contact(email="e@x.com", name="Efe Ade", status=SelarContact.Status.PAID)
        with django_capture_on_commit_callbacks(execute=True):
            send_selar_followups()
        with django_capture_on_commit_callbacks(execute=True):
            send_selar_followups()
        user = User.objects.get(email="e@x.com")
        assert not user.has_usable_password()
        assert user.first_name == "Efe"
        assert Enrollment.objects.filter(user=user, course=psr_course).count() == 1
        assert keys() == {"selar:buyer-welcome:e@x.com"}

    def test_site_buyer_is_not_sent_sales_emails(self, psr_course):
        user = User.objects.create_user(email="f@x.com", password="pw-12345678")
        Enrollment.objects.create(user=user, course=psr_course)
        record_contact(email="f@x.com", status=SelarContact.Status.ABANDONED)
        send_selar_followups()
        assert keys() == set()


@pytest.mark.django_db
class TestImportCommand:
    def test_csv_and_abandoned(self, tmp_path):
        path = tmp_path / "sales.csv"
        path.write_text(
            "Products(s),Customer Fullname,Customer Email,Customer Mobile,Reference,Transaction Date,Total\n"
            "FREE: 34 PSR,Christian Adigwe,CHRIS@X.COM,,S1,\"Oct 22nd 2026, 11:50 AM\",NGN 0\n"
            "PSR Complete Pack,Kehinde Ade,k@x.com,0803,S2,\"Oct 22nd 2026, 9:59 AM\",\"NGN 5,000\"\n",
            encoding="utf-8",
        )
        call_command("import_selar_contacts", csv=str(path), abandoned=["Ayombo Ogunyemi <ay@x.com>"])
        chris = SelarContact.objects.get(email="chris@x.com")
        assert (chris.name, chris.status) == ("Christian Adigwe", SelarContact.Status.FREE)
        assert chris.status_changed_at.day == 22
        assert SelarContact.objects.get(email="k@x.com").status == SelarContact.Status.PAID
        ay = SelarContact.objects.get(email="ay@x.com")
        assert (ay.name, ay.status) == ("Ayombo Ogunyemi", SelarContact.Status.ABANDONED)


def test_resend_payload_routes_replies_to_read_inbox(settings):
    from unittest.mock import MagicMock, patch

    from .gateway import ResendGateway

    settings.EMAIL_REPLY_TO = "contact@example.com"
    with patch("apps.engagement.gateway.requests.post") as post:
        post.return_value = MagicMock(status_code=200, json=lambda: {"id": "r1"})
        ResendGateway(api_key="k").send(to_email="a@x.com", from_email="academy@example.com", subject="s", html="h")
    assert post.call_args.kwargs["json"]["reply_to"] == ["contact@example.com"]
