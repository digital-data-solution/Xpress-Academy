from unittest.mock import patch

import pytest
from django.test import Client

from apps.catalog.models import Audience, Course, Programme
from apps.organizations.models import Organization

from .models import Profile, User
from .views import _make_reset_token, _make_verify_token


@pytest.mark.django_db
class TestAutoProfileSignal:
    def test_every_new_user_gets_a_profile(self):
        """Real bug this closes: the Phase 1 superuser had no Profile
        at all until this signal existed — anything touching
        user.profile (checkout does) would crash."""
        user = User.objects.create_user(email="new@example.com", password="testpass123")
        assert Profile.objects.filter(user=user).exists()

    def test_createsuperuser_path_also_gets_a_profile(self):
        user = User.objects.create_superuser(email="admin@example.com", password="testpass123")
        assert Profile.objects.filter(user=user).exists()


@pytest.mark.django_db
class TestSignup:
    def test_signup_creates_user_and_logs_in(self):
        client = Client()
        with patch("apps.engagement.services.ResendGateway.send"):
            resp = client.post("/account/signup/", {
                "first_name": "Ada", "last_name": "Learner", "email": "ada@example.com",
                "password": "a-genuinely-long-passphrase-123",
            })
        assert resp.status_code == 302
        user = User.objects.get(email="ada@example.com")
        assert user.first_name == "Ada"
        # logged in — dashboard should be reachable without another login
        resp = client.get("/dashboard/")
        assert resp.status_code == 200

    def test_signup_creates_unverified_profile(self):
        client = Client()
        client.post("/account/signup/", {
            "first_name": "Ada", "email": "ada2@example.com", "password": "a-genuinely-long-passphrase-123",
        })
        user = User.objects.get(email="ada2@example.com")
        assert user.profile.email_verified is False

    def test_duplicate_email_rejected(self):
        User.objects.create_user(email="dupe@example.com", password="testpass123")
        client = Client()
        resp = client.post("/account/signup/", {
            "first_name": "Ada", "email": "dupe@example.com", "password": "a-genuinely-long-passphrase-123",
        })
        assert resp.status_code == 200  # re-renders the form with an error
        assert User.objects.filter(email="dupe@example.com").count() == 1

    def test_weak_password_rejected(self):
        client = Client()
        resp = client.post("/account/signup/", {
            "first_name": "Ada", "email": "weak@example.com", "password": "12345",
        })
        assert resp.status_code == 200
        assert not User.objects.filter(email="weak@example.com").exists()


@pytest.mark.django_db
class TestEmailVerification:
    def test_valid_token_verifies(self):
        user = User.objects.create_user(email="verify@example.com", password="testpass123")
        token = _make_verify_token(user)
        client = Client()
        resp = client.get(f"/account/verify/{token}/")
        assert resp.status_code == 302
        user.profile.refresh_from_db()
        assert user.profile.email_verified is True

    def test_garbage_token_rejected(self):
        client = Client()
        resp = client.get("/account/verify/not-a-real-token/")
        assert resp.status_code == 302  # redirected to login with an error message, not a 500

    def test_tampered_token_rejected(self):
        user = User.objects.create_user(email="tamper@example.com", password="testpass123")
        token = _make_verify_token(user)
        tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
        client = Client()
        client.get(f"/account/verify/{tampered}/")
        user.profile.refresh_from_db()
        assert user.profile.email_verified is False


@pytest.mark.django_db
class TestCheckoutRequiresVerification:
    def test_unverified_user_blocked_from_checkout(self):
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        programme = Programme.objects.create(organization=org, title="P", audience=Audience.BREEDER)
        course = Course.objects.create(organization=org, programme=programme, title="C", audience=Audience.BREEDER, price_ngn=10000)

        user = User.objects.create_user(email="unverified@example.com", password="testpass123")
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{course.slug}/")
        assert resp.status_code == 200
        assert b"Verify your email" in resp.content

    def test_verified_user_reaches_checkout(self):
        org = Organization.objects.create(name="Test Org2", from_email="test2@example.com")
        programme = Programme.objects.create(organization=org, title="P2", audience=Audience.BREEDER)
        course = Course.objects.create(organization=org, programme=programme, title="C2", audience=Audience.BREEDER, price_ngn=10000)

        user = User.objects.create_user(email="verified@example.com", password="testpass123")
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{course.slug}/")
        assert resp.status_code == 200
        assert b"Pay with Paystack" in resp.content


@pytest.mark.django_db
class TestForgotPassword:
    def test_existing_email_sends_reset_and_shows_generic_message(self):
        User.objects.create_user(email="hasaccount@example.com", password="oldpassword123")
        client = Client()
        with patch("apps.engagement.services.ResendGateway.send"):
            resp = client.post("/account/forgot-password/", {"email": "hasaccount@example.com"}, follow=True)
        assert b"If that email has an account" in resp.content

    def test_unknown_email_shows_same_generic_message(self):
        """Doesn't confirm/deny an email is registered — see the
        view's own comment on why."""
        client = Client()
        resp = client.post("/account/forgot-password/", {"email": "nobody@example.com"}, follow=True)
        assert b"If that email has an account" in resp.content


@pytest.mark.django_db
class TestResetPassword:
    def test_valid_token_resets_password(self):
        user = User.objects.create_user(email="reset@example.com", password="oldpassword123")
        token = _make_reset_token(user)
        client = Client()
        resp = client.post(f"/account/reset-password/{token}/", {
            "new_password1": "a-genuinely-long-passphrase-456",
            "new_password2": "a-genuinely-long-passphrase-456",
        })
        assert resp.status_code == 302
        user.refresh_from_db()
        assert user.check_password("a-genuinely-long-passphrase-456")

    def test_token_is_single_use(self):
        """The password-hash-fragment trick: once the password has
        changed, the same link can't be replayed to set it again."""
        user = User.objects.create_user(email="onceonly@example.com", password="oldpassword123")
        token = _make_reset_token(user)
        client = Client()
        client.post(f"/account/reset-password/{token}/", {
            "new_password1": "first-new-passphrase-789",
            "new_password2": "first-new-passphrase-789",
        })
        resp = client.post(f"/account/reset-password/{token}/", {
            "new_password1": "second-attempt-passphrase-000",
            "new_password2": "second-attempt-passphrase-000",
        }, follow=True)
        assert b"already been used" in resp.content
        user.refresh_from_db()
        assert user.check_password("first-new-passphrase-789")

    def test_garbage_token_rejected(self):
        client = Client()
        resp = client.get("/account/reset-password/not-a-real-token/")
        assert resp.status_code == 302

    def test_mismatched_passwords_rejected(self):
        user = User.objects.create_user(email="mismatch@example.com", password="oldpassword123")
        token = _make_reset_token(user)
        client = Client()
        client.post(f"/account/reset-password/{token}/", {
            "new_password1": "one-passphrase-here-111",
            "new_password2": "a-different-passphrase-222",
        })
        user.refresh_from_db()
        assert user.check_password("oldpassword123")  # unchanged
