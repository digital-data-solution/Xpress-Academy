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


def test_nameless_contact_is_greeted_sir_ma():
    assert SelarContact(name="").first_name == "Sir/Ma"
    assert SelarContact(name="muniba yakubu").first_name == "Muniba"


@pytest.mark.django_db
class TestActivation:
    def test_claim_grants_access_and_reference_is_single_use(self, psr_course, client):
        r = client.post("/selar/activate/", {"name": "Efe Ade", "email": "e@x.com", "reference": "s466kf16168bx"})
        assert r.status_code == 200 and b"unlocked" in r.content
        c = SelarContact.objects.get(email="e@x.com")
        assert (c.status, c.reference, c.reference_verified) == (SelarContact.Status.PAID, "S466KF16168BX", False)
        assert Enrollment.objects.filter(user__email="e@x.com", course=psr_course).exists()

        r = client.post("/selar/activate/", {"name": "Friend", "email": "friend@x.com", "reference": "S466KF16168BX"})
        assert b"already been used" in r.content
        assert not User.objects.filter(email="friend@x.com").exists()

    def test_bad_reference_rejected(self, psr_course, client):
        r = client.post("/selar/activate/", {"name": "X", "email": "x@x.com", "reference": "12345"})
        assert b"starts with S" in r.content
        assert not SelarContact.objects.exists()

    def test_import_verifies_claim_and_reports_fakes(self, psr_course, client, tmp_path, capsys):
        client.post("/selar/activate/", {"name": "Real", "email": "real@x.com", "reference": "SREAL0000001"})
        client.post("/selar/activate/", {"name": "Fake", "email": "fake@x.com", "reference": "SFAKE0000001"})
        SelarContact.objects.update(created_at=timezone.now() - timedelta(days=3))
        path = tmp_path / "sales.csv"
        path.write_text(
            "Products(s),Customer Fullname,Customer Email,Reference,Transaction Date,Total\n"
            "PSR Complete Pack,Real Buyer,other@x.com,SREAL0000001,\"Oct 22nd 2026, 9:59 AM\",\"NGN 5,000\"\n",
            encoding="utf-8",
        )
        call_command("import_selar_contacts", csv=str(path))
        assert SelarContact.objects.get(email="real@x.com").reference_verified
        out = capsys.readouterr().out
        assert "fake@x.com" in out and "real@x.com" not in out


@pytest.mark.django_db
def test_office_account_gets_team_offer():
    c = record_contact(email="pid@x.com", name="PORTS INSPECTION DIRECTORATE YABA-LAGOS",
                       status=SelarContact.Status.FREE, when=timezone.now() - timedelta(days=5))
    assert c.is_office and c.first_name == "Sir/Ma"
    assert not SelarContact(name="Grace Osabo").is_office
    from django.template.loader import render_to_string
    from .selar import _context
    html = render_to_string("emails/selar_free_offer.html", _context(c))
    assert "Dear Sir/Ma" in html and "Team Pack: ₦35,000 for 10 officers" in html


@pytest.mark.django_db
def test_admin_import_page(client):
    admin_user = User.objects.create_superuser(email="boss@x.com", password="pw-12345678")
    client.force_login(admin_user)
    from django.urls import reverse
    url = reverse("admin:engagement_selarcontact_import")
    assert client.get(url).status_code == 200
    r = client.post(url, {
        "csv_text": "Customer Fullname,Customer Email,Transaction Date,Total\nAda Obi,ada@x.com,\"Oct 22nd 2026, 9:59 AM\",NGN 0\n",
        "abandoned": "Bayo Ade <bayo@x.com>", "send_now": "on",
    })
    assert r.status_code == 302
    assert SelarContact.objects.get(email="ada@x.com").status == SelarContact.Status.FREE
    assert SelarContact.objects.get(email="bayo@x.com").status == SelarContact.Status.ABANDONED
    assert EmailLog.objects.filter(dedupe_key="selar:abandoned-1:bayo@x.com").exists()
