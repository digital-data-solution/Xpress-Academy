"""Engagement isn't in build spec §11's explicit test list, but the
dedupe/windowing logic here is exactly the kind of thing that's silently
wrong without a test — a stalled-learner nudge that fires every day
instead of stopping at 3, or an expiry warning that double-sends, is a
real user-facing annoyance, not a theoretical bug."""

from datetime import datetime
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

from .gateway import ResendError
from .models import EmailLog, LiveSession
from .services import send_email
from .tasks import (
    detect_stalled_learners,
    expire_enrollments,
    expire_stale_attempts,
    remind_live_session,
    send_weekly_staff_training_email_task,
    unlock_dripped_modules,
    warn_expiring_access,
)


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience=Audience.BREEDER)
    return Course.objects.create(organization=org, programme=programme, title="Test Course", audience=Audience.BREEDER)


@pytest.fixture
def user():
    return User.objects.create_user(email="learner@example.com", password="testpass123", first_name="Ada")


def make_module(course, order=1, unlock_rule=Module.UnlockRule.SEQUENTIAL, drip_days=0):
    module = Module.objects.create(
        course=course, order=order, title=f"Module {order}", unlock_rule=unlock_rule, drip_days=drip_days,
    )
    Lesson.objects.create(module=module, order=1, title=f"Lesson {order}.1", type=Lesson.Type.TEXT)
    return module


@pytest.mark.django_db
class TestSendEmail:
    def test_no_api_key_configured_marks_sent_as_noop(self, settings):
        settings.RESEND_API_KEY = ""
        log = send_email(to_email="x@example.com", template_key="test", subject="Hi", html="<p>hi</p>")
        assert log.status == EmailLog.Status.SENT
        assert log.provider_id == "dev-noop"

    def test_dedupe_key_prevents_double_send(self, settings):
        settings.RESEND_API_KEY = "fake-key"
        with patch("apps.engagement.services.ResendGateway.send") as mock_send:
            mock_send.return_value = {"id": "resend-123"}
            send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>", dedupe_key="once")
            send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>", dedupe_key="once")
        assert mock_send.call_count == 1
        assert EmailLog.objects.filter(dedupe_key="once").count() == 1

    def test_gateway_failure_marks_failed_not_raised(self, settings):
        settings.RESEND_API_KEY = "fake-key"
        with patch("apps.engagement.services.ResendGateway.send") as mock_send:
            mock_send.side_effect = ResendError("simulated failure")
            log = send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>")
        assert log.status == EmailLog.Status.FAILED
        assert "simulated failure" in log.error

    def test_failed_dedupe_key_can_be_retried(self, settings):
        """A FAILED attempt (not SENT) under the same dedupe_key should
        be retryable, not silently stuck forever."""
        settings.RESEND_API_KEY = "fake-key"
        with patch("apps.engagement.services.ResendGateway.send") as mock_send:
            mock_send.side_effect = ResendError("down")
            send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>", dedupe_key="retry-me")

        with patch("apps.engagement.services.ResendGateway.send") as mock_send:
            mock_send.return_value = {"id": "ok-now"}
            log = send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>", dedupe_key="retry-me")

        assert log.status == EmailLog.Status.SENT
        assert EmailLog.objects.filter(dedupe_key="retry-me").count() == 1

    def test_smtp_fallback_used_when_no_resend_but_smtp_configured(self, settings):
        settings.RESEND_API_KEY = ""
        settings.EMAIL_HOST_USER = "sender@gmail.com"
        settings.EMAIL_HOST_PASSWORD = "app-password"
        with patch("apps.engagement.services._send_via_smtp") as mock_smtp:
            mock_smtp.return_value = "smtp"
            log = send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>")
        mock_smtp.assert_called_once()
        assert log.status == EmailLog.Status.SENT
        assert log.provider_id == "smtp"

    def test_resend_preferred_over_smtp_when_both_configured(self, settings):
        settings.RESEND_API_KEY = "fake-key"
        settings.EMAIL_HOST_USER = "sender@gmail.com"
        settings.EMAIL_HOST_PASSWORD = "app-password"
        with patch("apps.engagement.services.ResendGateway.send") as mock_resend, \
             patch("apps.engagement.services._send_via_smtp") as mock_smtp:
            mock_resend.return_value = {"id": "resend-1"}
            send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>")
        mock_resend.assert_called_once()
        mock_smtp.assert_not_called()

    def test_smtp_failure_marks_failed_not_raised(self, settings):
        settings.RESEND_API_KEY = ""
        settings.EMAIL_HOST_USER = "sender@gmail.com"
        settings.EMAIL_HOST_PASSWORD = "wrong-password"
        with patch("apps.engagement.services._send_via_smtp") as mock_smtp:
            mock_smtp.side_effect = Exception("(535) Authentication failed")
            log = send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>")
        assert log.status == EmailLog.Status.FAILED
        assert "Authentication failed" in log.error

    def test_no_config_at_all_falls_back_to_noop(self, settings):
        settings.RESEND_API_KEY = ""
        settings.EMAIL_HOST_USER = ""
        settings.EMAIL_HOST_PASSWORD = ""
        log = send_email(to_email="x@example.com", template_key="t", subject="s", html="<p>x</p>")
        assert log.status == EmailLog.Status.SENT
        assert log.provider_id == "dev-noop"


@pytest.mark.django_db
class TestStalledLearners:
    def test_sends_to_stalled_active_enrollment(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.last_activity_at = timezone.now() - timezone.timedelta(days=8)
        enrollment.save(update_fields=["last_activity_at"])

        sent = detect_stalled_learners()
        assert sent == 1
        assert EmailLog.objects.filter(template_key="stalled_nudge", to_email=user.email).exists()

    def test_does_not_send_to_recently_active_enrollment(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.last_activity_at = timezone.now() - timezone.timedelta(days=1)
        enrollment.save(update_fields=["last_activity_at"])

        assert detect_stalled_learners() == 0

    def test_stops_after_max_nudges(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.last_activity_at = timezone.now() - timezone.timedelta(days=8)
        enrollment.save(update_fields=["last_activity_at"])

        for i in range(3):
            EmailLog.objects.create(
                user=user, to_email=user.email, template_key="stalled_nudge", subject="x",
                status=EmailLog.Status.SENT, dedupe_key=f"stalled_nudge:{enrollment.id}:{i + 1}",
            )
        assert detect_stalled_learners() == 0


@pytest.mark.django_db
class TestExpiringAccess:
    def test_fires_at_14_day_window(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.expires_at = timezone.now() + timezone.timedelta(days=13, hours=12)
        enrollment.save(update_fields=["expires_at"])

        assert warn_expiring_access() == 1
        assert EmailLog.objects.filter(dedupe_key=f"expiring_access:{enrollment.id}:14").exists()

    def test_does_not_fire_outside_any_window(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.expires_at = timezone.now() + timezone.timedelta(days=20)
        enrollment.save(update_fields=["expires_at"])

        assert warn_expiring_access() == 0

    def test_does_not_double_fire_same_window(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.expires_at = timezone.now() + timezone.timedelta(days=2)
        enrollment.save(update_fields=["expires_at"])

        first = warn_expiring_access()
        second = warn_expiring_access()
        assert first == 1
        assert second == 0

    def test_lifetime_access_never_warned(self, course, user):
        Enrollment.objects.create(user=user, course=course)  # expires_at=None
        assert warn_expiring_access() == 0


@pytest.mark.django_db
class TestExpireEnrollments:
    def test_flips_past_expiry_active_to_expired(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.expires_at = timezone.now() - timezone.timedelta(days=1)
        enrollment.save(update_fields=["expires_at"])

        count = expire_enrollments()
        enrollment.refresh_from_db()
        assert count == 1
        assert enrollment.status == Enrollment.Status.EXPIRED

    def test_leaves_unexpired_active_alone(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.expires_at = timezone.now() + timezone.timedelta(days=1)
        enrollment.save(update_fields=["expires_at"])

        assert expire_enrollments() == 0


@pytest.mark.django_db
class TestUnlockDrippedModules:
    def test_sends_when_module_just_crossed_threshold(self, course, user):
        module = make_module(course, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=7, minutes=5)
        enrollment.save(update_fields=["started_at"])

        assert unlock_dripped_modules() == 1
        assert EmailLog.objects.filter(dedupe_key=f"module_unlocked:{enrollment.id}:{module.id}").exists()

    def test_no_send_when_not_yet_unlocked(self, course, user):
        make_module(course, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)  # started_at = now
        assert unlock_dripped_modules() == 0

    def test_still_sends_when_unlocked_long_ago(self, course, user):
        """Real fix, not just a rename: previously this task only sent
        inside a ±1-hour window around whenever it happened to run —
        under the once-daily free-tier cron (no real hourly beat yet),
        that meant a module unlocked hours before/after the daily run
        silently never got an email at all. Now it's dedupe_key alone
        guarding against a resend, not a time window, so "unlocked 30
        days ago, never processed before" still sends on first run."""
        make_module(course, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=30)
        enrollment.save(update_fields=["started_at"])
        assert unlock_dripped_modules() == 1

    def test_does_not_resend_on_a_later_run(self, course, user):
        module = make_module(course, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=30)
        enrollment.save(update_fields=["started_at"])

        assert unlock_dripped_modules() == 1
        assert unlock_dripped_modules() == 0  # already sent for this enrollment/module pair
        assert EmailLog.objects.filter(dedupe_key=f"module_unlocked:{enrollment.id}:{module.id}").count() == 1

    def test_pings_ops_for_compulsory_staff_training_course(self, course, settings):
        settings.OPS_ALERT_EMAIL = "ops@example.com"
        course.is_staff_training = True
        course.is_compulsory_staff_training = True
        course.save(update_fields=["is_staff_training", "is_compulsory_staff_training"])
        module = make_module(course, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        u = User.objects.create_user(email="trainee@example.com", password="testpass123")
        enrollment = Enrollment.objects.create(user=u, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=7, minutes=5)
        enrollment.save(update_fields=["started_at"])

        unlock_dripped_modules()

        assert EmailLog.objects.filter(
            to_email="ops@example.com", dedupe_key=f"compulsory_training_unlocked:{enrollment.id}:{module.id}"
        ).exists()

    def test_no_ops_ping_for_non_compulsory_course(self, settings, course, user):
        settings.OPS_ALERT_EMAIL = "ops@example.com"
        # course.is_compulsory_staff_training left False
        make_module(course, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=7, minutes=5)
        enrollment.save(update_fields=["started_at"])

        unlock_dripped_modules()

        assert EmailLog.objects.filter(to_email="ops@example.com").count() == 0


@pytest.mark.django_db
class TestLiveSessionReminders:
    def test_24h_window_fires(self, course, user):
        session = LiveSession.objects.create(course=course, title="Q&A", starts_at=timezone.now() + timezone.timedelta(hours=23))
        Enrollment.objects.create(user=user, course=course)
        assert remind_live_session() == 1
        assert EmailLog.objects.filter(dedupe_key__contains="24h").exists()

    def test_no_double_send_same_window(self, course, user):
        LiveSession.objects.create(course=course, title="Q&A", starts_at=timezone.now() + timezone.timedelta(minutes=30))
        Enrollment.objects.create(user=user, course=course)
        first = remind_live_session()
        second = remind_live_session()
        assert first == 1
        assert second == 0

    def test_cancelled_session_not_reminded(self, course, user):
        LiveSession.objects.create(
            course=course, title="Q&A", starts_at=timezone.now() + timezone.timedelta(hours=1), is_cancelled=True,
        )
        Enrollment.objects.create(user=user, course=course)
        assert remind_live_session() == 0

    def test_far_future_session_not_yet_reminded(self, course, user):
        LiveSession.objects.create(course=course, title="Q&A", starts_at=timezone.now() + timezone.timedelta(days=5))
        Enrollment.objects.create(user=user, course=course)
        assert remind_live_session() == 0


@pytest.mark.django_db
class TestExpireStaleAttemptsTask:
    def test_wraps_bulk_expiry(self, course, user):
        from apps.assessment.models import Choice, Question, QuestionBank, Quiz
        from apps.assessment.services import start_attempt

        bank = QuestionBank.objects.create(organization=course.organization, name="Bank")
        q = Question.objects.create(bank=bank, type=Question.Type.MCQ, stem="Q")
        Choice.objects.create(question=q, text="A", is_correct=True, order=1)
        Choice.objects.create(question=q, text="B", is_correct=False, order=2)
        quiz = Quiz.objects.create(scope=Quiz.Scope.FINAL, course=course, title="Final", bank=bank, question_count=1, time_limit_minutes=10)
        enrollment = Enrollment.objects.create(user=user, course=course)

        attempt = start_attempt(enrollment, quiz)
        attempt.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        attempt.save(update_fields=["expires_at"])

        result = expire_stale_attempts.delay().get()
        assert result == 1
        attempt.refresh_from_db()
        assert attempt.submitted_at is not None


@pytest.mark.django_db
class TestWeeklyStaffTrainingEmail:
    """Recipients are defined entirely by Enrollment, not is_staff —
    see apps.engagement.tasks.send_weekly_staff_training_email_task's
    docstring and apps.catalog.views for why. A plain, non-admin
    account enrolled in an is_staff_training course is a recipient; an
    is_staff/is_superuser account with no such enrollment is not."""

    MONDAY = datetime(2026, 8, 24, 9, 0)  # a real Monday
    TUESDAY = datetime(2026, 8, 25, 9, 0)  # a real Tuesday

    def _staff_training_course(self, course):
        course.is_staff_training = True
        course.is_published = True
        course.review_status = Course.ReviewStatus.APPROVED
        course.save(update_fields=["is_staff_training", "is_published", "review_status"])
        return course

    def test_skips_on_non_monday(self, org, course, user):
        self._staff_training_course(course)
        Enrollment.objects.create(user=user, course=course)
        with patch("apps.engagement.tasks.timezone.localtime", return_value=self.TUESDAY):
            result = send_weekly_staff_training_email_task()
        assert result == "skipped (not Monday)"
        assert EmailLog.objects.count() == 0

    def test_skips_when_no_staff_training_enrollments(self, org, course, user):
        self._staff_training_course(course)
        # no Enrollment created — course is published but nobody's enrolled in it
        with patch("apps.engagement.tasks.timezone.localtime", return_value=self.MONDAY), \
             patch("apps.engagement.tasks.timezone.localdate", return_value=self.MONDAY.date()):
            result = send_weekly_staff_training_email_task()
        assert result == "skipped (no staff-training enrollments)"

    def test_sends_only_to_enrolled_users(self, org, course):
        self._staff_training_course(course)
        trainee = User.objects.create_user(email="trainee@example.com", password="testpass123")
        Enrollment.objects.create(user=trainee, course=course)
        # An admin account with no enrollment in this course — must NOT receive it.
        admin = User.objects.create_user(email="owner@example.com", password="testpass123")
        admin.is_staff = True
        admin.is_superuser = True
        admin.save(update_fields=["is_staff", "is_superuser"])

        with patch("apps.engagement.tasks.timezone.localtime", return_value=self.MONDAY), \
             patch("apps.engagement.tasks.timezone.localdate", return_value=self.MONDAY.date()):
            result = send_weekly_staff_training_email_task()

        assert result == "sent 1"
        assert EmailLog.objects.filter(
            to_email="trainee@example.com", template_key="staff_training_weekly"
        ).count() == 1
        assert EmailLog.objects.filter(to_email="owner@example.com").count() == 0

    def test_idempotent_same_monday(self, org, course, user):
        self._staff_training_course(course)
        Enrollment.objects.create(user=user, course=course)

        with patch("apps.engagement.tasks.timezone.localtime", return_value=self.MONDAY), \
             patch("apps.engagement.tasks.timezone.localdate", return_value=self.MONDAY.date()):
            send_weekly_staff_training_email_task()
            send_weekly_staff_training_email_task()

        assert EmailLog.objects.filter(
            to_email=user.email, template_key="staff_training_weekly"
        ).count() == 1


@pytest.mark.django_db(transaction=True)
class TestEmailWiring:
    """transaction=True is required here, not optional: both
    grant_access and issue_certificate queue their email via
    transaction.on_commit(), which Django only ever fires on a real
    commit. pytest-django's default django_db fixture wraps a test in
    one transaction that's rolled back at the end — on_commit callbacks
    registered inside it correctly never fire, so under the default
    fixture these tests would appear to fail even though the
    production code is right. This isn't a workaround for a bug; it's
    the correct way to test on_commit behaviour at all."""

    def test_grant_access_sends_welcome_email(self, course, user):
        from apps.payments.services import grant_access
        from apps.payments.models import Payment

        payment = Payment.objects.create(user=user, course=course, reference="XDA-test-welcome", amount_kobo=100000)
        verify_data = {"status": "success", "amount": 100000, "currency": "NGN", "reference": payment.reference, "metadata": {"product": "xpress_academy"}}
        grant_access(payment, verify_data)

        assert EmailLog.objects.filter(template_key="welcome", to_email=user.email).exists()

    def test_issue_certificate_sends_certificate_email(self, course, user):
        from apps.enrollment.services import mark_lesson_complete
        from apps.certificates.models import Certificate

        m1 = make_module(course)
        enrollment = Enrollment.objects.create(user=user, course=course)
        mark_lesson_complete(enrollment, m1.lessons.first())

        assert Certificate.objects.filter(enrollment=enrollment).exists()
        assert EmailLog.objects.filter(template_key="certificate_issued", to_email=user.email).exists()


@pytest.mark.django_db
class TestRunScheduledTasksEndpoint:
    def test_no_secret_configured_refuses_everyone(self, settings, client):
        settings.CRON_SECRET = ""
        resp = client.post("/internal/run-scheduled-tasks/", HTTP_X_CRON_SECRET="anything")
        assert resp.status_code == 403

    def test_wrong_secret_refused(self, settings, client):
        settings.CRON_SECRET = "the-real-secret"
        resp = client.post("/internal/run-scheduled-tasks/", HTTP_X_CRON_SECRET="wrong")
        assert resp.status_code == 403

    def test_get_not_allowed(self, settings, client):
        settings.CRON_SECRET = "the-real-secret"
        resp = client.get("/internal/run-scheduled-tasks/", HTTP_X_CRON_SECRET="the-real-secret")
        assert resp.status_code == 405

    def test_correct_secret_runs_tasks(self, settings, client):
        settings.CRON_SECRET = "the-real-secret"
        with patch("apps.payments.services.PaystackGateway.list_transactions") as mock_list:
            mock_list.return_value = {"data": []}
            resp = client.post("/internal/run-scheduled-tasks/", HTTP_X_CRON_SECRET="the-real-secret")
        assert resp.status_code == 200
        body = resp.json()
        assert "detect_stalled_learners" in body["ran"]
