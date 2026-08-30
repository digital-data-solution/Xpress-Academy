from unittest.mock import patch

import pytest
from django.contrib.auth.models import Group
from django.test import Client

from apps.catalog.models import Audience, Course, Programme
from apps.organizations.models import Organization

from .models import LoginAttempt, Profile, User
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
class TestCompulsoryTrainingAutoEnroll:
    def _compulsory_course(self, org):
        from apps.enrollment.models import Enrollment  # noqa: F401 — imported for clarity at call sites
        programme = Programme.objects.create(organization=org, title="Staff Training", audience=Audience.GENERAL)
        return Course.objects.create(
            organization=org, programme=programme, title="General Onboarding", slug="general-onboarding",
            audience=Audience.GENERAL, pricing_model=Course.PricingModel.FREE, is_published=True,
            review_status=Course.ReviewStatus.APPROVED, is_staff_training=True, is_compulsory_staff_training=True,
        )

    def test_joining_a_group_enrolls_in_compulsory_course(self):
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        course = self._compulsory_course(org)
        group = Group.objects.create(name="Course Manager")
        user = User.objects.create_user(email="new-hire@example.com", password="testpass123")

        user.groups.add(group)

        from apps.enrollment.models import Enrollment
        assert Enrollment.objects.filter(user=user, course=course).exists()

    def test_joining_a_group_sends_immediate_welcome_email(self):
        """Real fix, not just enrollment: without this, a new hire's
        first automatic notice would be up to 6 days late, waiting on
        the Monday weekly-reminder task. This must fire the moment
        they're added to a group, not later."""
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        course = self._compulsory_course(org)
        group = Group.objects.create(name="Course Manager")
        user = User.objects.create_user(email="new-hire4@example.com", password="testpass123")

        user.groups.add(group)

        from apps.engagement.models import EmailLog
        assert EmailLog.objects.filter(
            to_email=user.email, template_key="chain_course_unlocked",
            dedupe_key=f"chain_unlocked:{user.id}:{course.id}",
        ).exists()

    def test_re_adding_to_group_does_not_resend_welcome_email(self):
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        course = self._compulsory_course(org)
        group = Group.objects.create(name="Course Manager")
        user = User.objects.create_user(email="new-hire5@example.com", password="testpass123")

        user.groups.add(group)
        user.groups.remove(group)
        user.groups.add(group)  # re-added — enrollment already existed, so no second email either

        from apps.engagement.models import EmailLog
        assert EmailLog.objects.filter(
            to_email=user.email, template_key="chain_course_unlocked",
        ).count() == 1

    def test_non_compulsory_staff_training_course_not_auto_enrolled(self):
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        programme = Programme.objects.create(organization=org, title="Staff Training", audience=Audience.GENERAL)
        elective = Course.objects.create(
            organization=org, programme=programme, title="Elective Course", slug="elective-course",
            audience=Audience.GENERAL, pricing_model=Course.PricingModel.FREE, is_published=True,
            review_status=Course.ReviewStatus.APPROVED, is_staff_training=True,
            is_compulsory_staff_training=False,  # not the compulsory track
        )
        group = Group.objects.create(name="Course Manager")
        user = User.objects.create_user(email="new-hire2@example.com", password="testpass123")

        user.groups.add(group)

        from apps.enrollment.models import Enrollment
        assert not Enrollment.objects.filter(user=user, course=elective).exists()

    def test_ordinary_signup_with_no_group_is_not_enrolled(self):
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        self._compulsory_course(org)
        user = User.objects.create_user(email="plain-learner@example.com", password="testpass123")

        from apps.enrollment.models import Enrollment
        assert not Enrollment.objects.filter(user=user).exists()

    def test_idempotent_if_group_membership_changes_again(self):
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        course = self._compulsory_course(org)
        group = Group.objects.create(name="Course Manager")
        user = User.objects.create_user(email="new-hire3@example.com", password="testpass123")

        user.groups.add(group)
        user.groups.remove(group)
        user.groups.add(group)  # re-added — must not create a second Enrollment

        from apps.enrollment.models import Enrollment
        assert Enrollment.objects.filter(user=user, course=course).count() == 1

    def test_required_group_course_only_enrolls_that_groups_members(self):
        """Real bug this closes: adding a second role-specific
        compulsory course (e.g. Instructor Onboarding alongside
        Manager Onboarding) without this scoping would force every
        staff member through every role's training, not just their
        own — see Course.required_group's docstring."""
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        programme = Programme.objects.create(organization=org, title="Staff Training", audience=Audience.GENERAL)
        manager_group = Group.objects.create(name="Course Manager")
        scoped_course = Course.objects.create(
            organization=org, programme=programme, title="Manager Onboarding", slug="manager-onboarding-scoped",
            audience=Audience.GENERAL, pricing_model=Course.PricingModel.FREE, is_published=True,
            review_status=Course.ReviewStatus.APPROVED, is_staff_training=True, is_compulsory_staff_training=True,
            required_group=manager_group,
        )

        other_group = Group.objects.create(name="Support")
        outsider = User.objects.create_user(email="support-hire@example.com", password="testpass123")
        outsider.groups.add(other_group)

        from apps.enrollment.models import Enrollment
        assert not Enrollment.objects.filter(user=outsider, course=scoped_course).exists()

        manager_hire = User.objects.create_user(email="manager-hire@example.com", password="testpass123")
        manager_hire.groups.add(manager_group)
        assert Enrollment.objects.filter(user=manager_hire, course=scoped_course).exists()

    def test_unscoped_course_still_enrolls_regardless_of_which_group(self):
        """The universal case (required_group left blank, e.g. General
        Onboarding) must keep working exactly as before — scoping is
        opt-in per course, not a behavior change for existing courses."""
        org = Organization.objects.create(name="Test Org", from_email="test@example.com")
        course = self._compulsory_course(org)  # required_group left blank
        group = Group.objects.create(name="Support")
        user = User.objects.create_user(email="any-hire@example.com", password="testpass123")

        user.groups.add(group)

        from apps.enrollment.models import Enrollment
        assert Enrollment.objects.filter(user=user, course=course).exists()


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
class TestResendVerificationRateLimit:
    def test_rapid_repeated_clicks_only_send_once(self):
        """The real incident this guards against: a logged-in user
        (or a stuck double-submit) clicking "Resend verification
        email" repeatedly generated a real send every single time —
        six identical emails inside about a minute, confirmed via
        Resend's own delivery log. Only the first of several rapid
        clicks should actually dispatch."""
        from apps.engagement.models import EmailLog

        user = User.objects.create_user(email="clicker@example.com", password="testpass123")
        client = Client()
        client.force_login(user)
        for _ in range(6):
            resp = client.post("/account/resend-verification/", follow=True)
            assert resp.status_code == 200
        # user was created directly via create_user(), not the signup view,
        # so only the first of these 6 rapid resend clicks should have sent.
        assert EmailLog.objects.filter(template_key="verify_email", user=user, status=EmailLog.Status.SENT).count() == 1

    def test_already_verified_user_gets_no_email_regardless(self):
        from apps.engagement.models import EmailLog

        user = User.objects.create_user(email="already@example.com", password="testpass123")
        user.profile.email_verified = True
        user.profile.save(update_fields=["email_verified"])
        client = Client()
        client.force_login(user)
        client.post("/account/resend-verification/", follow=True)
        assert not EmailLog.objects.filter(template_key="verify_email", user=user).exists()


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

    def test_rapid_repeated_submissions_only_send_once(self):
        """The real incident this guards against: nothing previously
        stopped anyone — no login required — from repeatedly
        submitting this public form for a known email and generating a
        real email every single time. Same generic message either way,
        but only the first of several rapid submissions should
        actually dispatch."""
        from apps.engagement.models import EmailLog

        User.objects.create_user(email="spammed@example.com", password="oldpassword123")
        client = Client()
        for _ in range(6):
            resp = client.post("/account/forgot-password/", {"email": "spammed@example.com"}, follow=True)
            assert b"If that email has an account" in resp.content  # identical message every time
        assert EmailLog.objects.filter(template_key="password_reset", status=EmailLog.Status.SENT).count() == 1


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


@pytest.mark.django_db
class TestLoginBruteForceProtection:
    """Django's stock LoginView (used directly in urls.py) has zero
    built-in throttling — this is the fix. See
    RateLimitedAuthenticationForm and LoginAttempt."""

    def test_locks_out_after_threshold_failures(self):
        User.objects.create_user(email="target@example.com", password="the-real-password-123")
        client = Client()
        for _ in range(5):
            resp = client.post("/account/login/", {"username": "target@example.com", "password": "wrong"})
            assert resp.status_code == 200  # re-renders the login form, doesn't log in

        # Even the CORRECT password is now blocked — the whole point.
        resp = client.post("/account/login/", {
            "username": "target@example.com", "password": "the-real-password-123",
        }, follow=True)
        assert b"Too many failed login attempts" in resp.content
        assert not resp.wsgi_request.user.is_authenticated

    def test_correct_password_still_works_under_the_threshold(self):
        User.objects.create_user(email="normal@example.com", password="the-real-password-456")
        client = Client()
        for _ in range(3):
            client.post("/account/login/", {"username": "normal@example.com", "password": "wrong"})

        resp = client.post("/account/login/", {
            "username": "normal@example.com", "password": "the-real-password-456",
        })
        assert resp.status_code == 302  # real login succeeds and redirects

    def test_failed_and_successful_attempts_are_recorded(self):
        User.objects.create_user(email="recorded@example.com", password="the-real-password-789")
        client = Client()
        client.post("/account/login/", {"username": "recorded@example.com", "password": "wrong"})
        client.post("/account/login/", {"username": "recorded@example.com", "password": "the-real-password-789"})

        assert LoginAttempt.objects.filter(email="recorded@example.com", successful=False).count() == 1
        assert LoginAttempt.objects.filter(email="recorded@example.com", successful=True).count() == 1

    def test_lockout_is_per_email_not_global(self):
        """A different account's login attempts must not be affected
        by someone else being locked out."""
        User.objects.create_user(email="victim@example.com", password="victim-password-123")
        User.objects.create_user(email="bystander@example.com", password="bystander-password-456")
        client = Client()
        for _ in range(5):
            client.post("/account/login/", {"username": "victim@example.com", "password": "wrong"})

        resp = client.post("/account/login/", {
            "username": "bystander@example.com", "password": "bystander-password-456",
        })
        assert resp.status_code == 302  # unaffected by victim@example.com's lockout


def _current_totp(device):
    from django_otp.oath import totp
    return "%06d" % totp(device.bin_key)


@pytest.mark.django_db
class TestTwoFactorSetup:
    def test_get_shows_qr_and_secret_for_a_new_device(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-setup@example.com", password="testpass123")
        client = Client()
        client.force_login(user)

        resp = client.get("/account/2fa/setup/")

        assert resp.status_code == 200
        assert TOTPDevice.objects.filter(user=user, confirmed=False).exists()
        assert b"data:image/png;base64," in resp.content

    def test_correct_code_confirms_device_and_shows_backup_codes(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django_otp.plugins.otp_static.models import StaticDevice

        user = User.objects.create_user(email="2fa-confirm@example.com", password="testpass123")
        client = Client()
        client.force_login(user)
        client.get("/account/2fa/setup/")  # creates the unconfirmed device
        device = TOTPDevice.objects.get(user=user, confirmed=False)

        resp = client.post("/account/2fa/setup/", {"token": _current_totp(device)})

        device.refresh_from_db()
        assert device.confirmed is True
        assert resp.status_code == 200
        assert b"Save your backup codes" in resp.content
        static = StaticDevice.objects.get(user=user)
        assert static.token_set.count() == 10

    def test_wrong_code_does_not_confirm_the_device(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-wrong@example.com", password="testpass123")
        client = Client()
        client.force_login(user)
        client.get("/account/2fa/setup/")

        client.post("/account/2fa/setup/", {"token": "000000"})

        device = TOTPDevice.objects.get(user=user)
        assert device.confirmed is False

    def test_already_enabled_offers_disable_not_a_new_qr(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-already@example.com", password="testpass123")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        client = Client()
        client.force_login(user)

        resp = client.get("/account/2fa/setup/")

        assert b"already enabled" in resp.content
        assert b"data:image/png;base64," not in resp.content

    def test_disable_requires_correct_password(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-disable@example.com", password="the-real-password")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        client = Client()
        client.force_login(user)

        resp = client.post("/account/2fa/disable/", {"password": "wrong-password"}, follow=True)
        assert TOTPDevice.objects.filter(user=user, confirmed=True).exists()
        assert b"NOT disabled" in resp.content

        client.post("/account/2fa/disable/", {"password": "the-real-password"})
        assert not TOTPDevice.objects.filter(user=user).exists()

    def test_a_non_staff_learner_can_still_opt_in(self):
        """2FA enforcement at login is opt-in-driven, not is_staff-gated
        — anyone who wants it can set it up, staff or not."""
        user = User.objects.create_user(email="2fa-learner@example.com", password="testpass123", is_staff=False)
        client = Client()
        client.force_login(user)

        resp = client.get("/account/2fa/setup/")
        assert resp.status_code == 200


@pytest.mark.django_db
class TestTwoFactorLogin:
    def test_user_without_a_device_logs_in_normally(self):
        User.objects.create_user(email="no-2fa@example.com", password="testpass123")
        client = Client()

        resp = client.post("/account/login/", {"username": "no-2fa@example.com", "password": "testpass123"})

        assert resp.status_code == 302
        assert resp.wsgi_request.session.get("_auth_user_id")

    def test_staff_without_a_device_gets_a_setup_nudge(self):
        User.objects.create_user(email="staff-no-2fa@example.com", password="testpass123", is_staff=True)
        client = Client()

        resp = client.post("/account/login/", {
            "username": "staff-no-2fa@example.com", "password": "testpass123",
        }, follow=True)

        assert b"set it up now" in resp.content

    def test_user_with_confirmed_device_is_not_logged_in_until_verified(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-login@example.com", password="testpass123")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        client = Client()

        resp = client.post("/account/login/", {"username": "2fa-login@example.com", "password": "testpass123"})

        assert resp.status_code == 302
        assert resp.url == "/account/2fa/verify/"
        assert not resp.wsgi_request.session.get("_auth_user_id")
        assert client.session.get("pending_2fa_user_id") == user.pk

    def test_correct_totp_code_completes_login(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-verify@example.com", password="testpass123")
        device = TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        client = Client()
        client.post("/account/login/", {"username": "2fa-verify@example.com", "password": "testpass123"})

        resp = client.post("/account/2fa/verify/", {"token": _current_totp(device)})

        assert resp.status_code == 302
        assert client.session.get("_auth_user_id") == str(user.pk)

    def test_wrong_totp_code_does_not_log_in(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-wrong-verify@example.com", password="testpass123")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        client = Client()
        client.post("/account/login/", {"username": "2fa-wrong-verify@example.com", "password": "testpass123"})

        resp = client.post("/account/2fa/verify/", {"token": "000000"})

        assert resp.status_code == 200  # re-renders, no login
        assert not client.session.get("_auth_user_id")

    def test_backup_code_works_once_then_fails_the_second_time(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

        user = User.objects.create_user(email="2fa-backup@example.com", password="testpass123")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        static = StaticDevice.objects.create(user=user, confirmed=True, name="backup codes")
        StaticToken.objects.create(device=static, token="abcd1234")

        client = Client()
        client.post("/account/login/", {"username": "2fa-backup@example.com", "password": "testpass123"})
        resp = client.post("/account/2fa/verify/", {"token": "abcd1234"})
        assert client.session.get("_auth_user_id") == str(user.pk)

        client.logout()
        client.post("/account/login/", {"username": "2fa-backup@example.com", "password": "testpass123"})
        resp = client.post("/account/2fa/verify/", {"token": "abcd1234"})  # already consumed
        assert resp.status_code == 200
        assert not client.session.get("_auth_user_id")

    def test_locks_out_of_the_pending_challenge_after_too_many_wrong_codes(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="2fa-lockout@example.com", password="testpass123")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")
        client = Client()
        client.post("/account/login/", {"username": "2fa-lockout@example.com", "password": "testpass123"})

        for _ in range(5):
            client.post("/account/2fa/verify/", {"token": "000000"})

        # The pending challenge is gone now — even hitting verify again
        # bounces back to login instead of re-rendering the code form.
        resp = client.get("/account/2fa/verify/")
        assert resp.status_code == 302
        assert resp.url == "/account/login/"

    def test_admin_direct_login_routes_through_the_same_2fa_aware_view(self):
        """Real gap this closes: Django admin has its own separate
        built-in login form (AdminSite.login) — a staff member going
        straight to the admin URL with an expired session would
        otherwise authenticate through Django's stock form, bypassing
        2FA entirely, even though it's fully wired on /account/login/."""
        client = Client()
        resp = client.get("/admin/login/?next=/admin/")
        assert resp.status_code == 302
        assert resp.url == "/account/login/?next=/admin/"


@pytest.mark.django_db
class TestTwoFactorRecovery:
    """Real gap: self-service disable (accounts:twofactor_disable) needs
    an authenticated session — exactly what's unavailable to someone
    stuck at the 2FA prompt with a lost authenticator and no backup
    codes left. Two recovery paths, for two different situations."""

    def test_admin_action_resets_a_staff_members_2fa(self):
        """The common case: someone else with admin access resets a
        locked-out staff member's 2FA for them."""
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django_otp.plugins.otp_static.models import StaticDevice

        owner = User.objects.create_superuser(email="owner@example.com", password="testpass123")
        locked_out = User.objects.create_user(email="locked-out@example.com", password="testpass123", is_staff=True)
        TOTPDevice.objects.create(user=locked_out, confirmed=True, name="default")
        StaticDevice.objects.create(user=locked_out, confirmed=True, name="backup codes")

        client = Client()
        client.force_login(owner)
        client.post("/admin/accounts/user/", {
            "action": "reset_two_factor", "_selected_action": [str(locked_out.pk)],
        })

        assert not TOTPDevice.objects.filter(user=locked_out).exists()
        assert not StaticDevice.objects.filter(user=locked_out).exists()

        # And they can now log in with just the password again.
        client2 = Client()
        resp = client2.post("/account/login/", {
            "username": "locked-out@example.com", "password": "testpass123",
        })
        assert resp.status_code == 302
        assert resp.url != "/account/2fa/verify/"

    def test_management_command_resets_2fa_without_any_web_session(self):
        """The escape hatch for when the OWNER's own account is what's
        locked out — no admin login needed at all, runs straight
        against the database (same shape as every other one-off
        production command this project)."""
        from io import StringIO

        from django.core.management import call_command
        from django_otp.plugins.otp_totp.models import TOTPDevice

        user = User.objects.create_user(email="owner-locked-out@example.com", password="testpass123")
        TOTPDevice.objects.create(user=user, confirmed=True, name="default")

        out = StringIO()
        call_command("reset_2fa", "--email=owner-locked-out@example.com", stdout=out)

        assert not TOTPDevice.objects.filter(user=user).exists()
        assert "reset for owner-locked-out@example.com" in out.getvalue()

    def test_management_command_errors_on_unknown_email(self):
        from django.core.management import CommandError, call_command

        with pytest.raises(CommandError):
            call_command("reset_2fa", "--email=nobody@example.com")
