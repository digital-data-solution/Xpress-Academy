"""Coverage required by the payments addendum §6 before Phase 6 is
considered done. All Paystack HTTP calls are mocked — no real network
calls, no real keys needed to run this suite."""

import threading
import time
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Audience, Course, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

from .gateway import PaystackError
from .models import Coupon, Partner, Payment
from .services import (
    CouponInvalid,
    PaymentInitError,
    compute_amount_kobo,
    grant_access,
    initialize_payment,
    reconcile_pending_payments,
    sweep_paystack_transactions,
    verify_and_grant,
)


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience=Audience.BREEDER)
    return Course.objects.create(
        organization=org, programme=programme, title="Test Course", audience=Audience.BREEDER, price_ngn=45000,
    )


@pytest.fixture
def user():
    u = User.objects.create_user(email="learner@example.com", password="testpass123")
    # Checkout now gates on email verification (Phase 8) — verified by
    # default here since that's not what these tests are about.
    u.profile.email_verified = True
    u.profile.save(update_fields=["email_verified"])
    return u


def make_payment(user, course, amount_kobo=None):
    from .services import generate_reference
    return Payment.objects.create(
        user=user, course=course, reference=generate_reference(course, user),
        amount_kobo=amount_kobo or compute_amount_kobo(course),
    )


def verify_response(*, status="success", amount=4_500_000, reference, currency="NGN", product="xpress_academy"):
    return {
        "status": True,
        "message": "ok",
        "data": {
            "status": status, "amount": amount, "currency": currency,
            "reference": reference, "metadata": {"product": product},
        },
    }


@pytest.mark.django_db
class TestComputeAmount:
    def test_no_coupon(self, course):
        assert compute_amount_kobo(course) == 4_500_000

    def test_percent_coupon(self, course):
        coupon = Coupon.objects.create(code="SAVE10", discount_type=Coupon.DiscountType.PERCENT, value=10)
        assert compute_amount_kobo(course, coupon) == 4_050_000

    def test_fixed_coupon(self, course):
        coupon = Coupon.objects.create(code="N5000OFF", discount_type=Coupon.DiscountType.FIXED, value=500_000)
        assert compute_amount_kobo(course, coupon) == 4_000_000

    def test_never_goes_below_minimum_charge(self, course):
        coupon = Coupon.objects.create(code="HUGE", discount_type=Coupon.DiscountType.FIXED, value=10_000_000)
        assert compute_amount_kobo(course, coupon) == 100


@pytest.mark.django_db
class TestInitializePayment:
    def test_includes_callback_url_and_metadata_product(self, user, course):
        """Addendum §6, first required test."""
        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            initialize_payment(user=user, course=course)

        _args, kwargs = mock_init.call_args
        assert kwargs["callback_url"].endswith("/checkout/return/")
        assert kwargs["metadata"]["product"] == "xpress_academy"

    def test_payment_row_created_before_paystack_call(self, user, course):
        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            def check_payment_exists_already(**kwargs):
                assert Payment.objects.filter(reference=kwargs["reference"]).exists()
                return {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            mock_init.side_effect = check_payment_exists_already
            initialize_payment(user=user, course=course)

    def test_paystack_failure_marks_payment_failed_not_lost(self, user, course):
        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.side_effect = PaystackError("simulated network failure")
            with pytest.raises(PaymentInitError):
                initialize_payment(user=user, course=course)
        payment = Payment.objects.get(user=user, course=course)
        assert payment.status == Payment.Status.FAILED

    def test_invalid_coupon_code_rejected(self, user, course):
        with pytest.raises(CouponInvalid):
            initialize_payment(user=user, course=course, coupon_code="NOPE")

    def test_expired_coupon_rejected(self, user, course):
        Coupon.objects.create(
            code="OLD", discount_type=Coupon.DiscountType.PERCENT, value=10,
            valid_until=timezone.now() - timezone.timedelta(days=1),
        )
        with pytest.raises(CouponInvalid):
            initialize_payment(user=user, course=course, coupon_code="OLD")

    def test_maxed_out_coupon_rejected(self, user, course):
        Coupon.objects.create(
            code="MAXED", discount_type=Coupon.DiscountType.PERCENT, value=10, max_uses=1, times_used=1,
        )
        with pytest.raises(CouponInvalid):
            initialize_payment(user=user, course=course, coupon_code="MAXED")


@pytest.mark.django_db
class TestVerifyAndGrant:
    def test_unknown_reference_grants_nothing(self):
        """Addendum §6: "Return handler with a tampered reference in
        the query string grants nothing." """
        payment, error = verify_and_grant("XDA-does-not-exist")
        assert payment is None
        assert error
        assert Enrollment.objects.count() == 0

    def test_paystack_reports_failed_grants_nothing(self, user, course):
        payment = make_payment(user, course)
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(status="failed", reference=payment.reference, amount=payment.amount_kobo)
            result_payment, error = verify_and_grant(payment.reference)

        assert error is not None
        assert result_payment.status == Payment.Status.FAILED
        assert Enrollment.objects.count() == 0

    def test_mismatched_amount_grants_nothing_and_marks_failed(self, user, course):
        payment = make_payment(user, course)
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(reference=payment.reference, amount=payment.amount_kobo - 1)
            result_payment, error = verify_and_grant(payment.reference)

        assert error is not None
        assert result_payment.status == Payment.Status.FAILED
        assert Enrollment.objects.count() == 0

    def test_wrong_metadata_product_grants_nothing(self, user, course):
        payment = make_payment(user, course)
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(reference=payment.reference, amount=payment.amount_kobo, product="xpress_vet")
            result_payment, error = verify_and_grant(payment.reference)

        assert error is not None
        assert Enrollment.objects.count() == 0

    def test_valid_success_grants_access(self, user, course):
        payment = make_payment(user, course)
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(reference=payment.reference, amount=payment.amount_kobo)
            result_payment, error = verify_and_grant(payment.reference)

        assert error is None
        assert result_payment.status == Payment.Status.SUCCESS
        assert Enrollment.objects.filter(user=user, course=course, status=Enrollment.Status.ACTIVE).exists()

    def test_already_success_is_idempotent_no_reverify_call(self, user, course):
        payment = make_payment(user, course)
        payment.status = Payment.Status.SUCCESS
        payment.save(update_fields=["status"])
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            _payment, error = verify_and_grant(payment.reference)
            mock_verify.assert_not_called()
        assert error is None


@pytest.mark.django_db
class TestGrantAccessIdempotency:
    def test_called_twice_creates_exactly_one_enrollment(self, user, course):
        """Addendum §6: "grant_access() called twice with the same
        payment creates exactly one Enrollment." """
        payment = make_payment(user, course)
        verify_data = verify_response(reference=payment.reference, amount=payment.amount_kobo)["data"]

        grant_access(payment, verify_data)
        payment.refresh_from_db()
        grant_access(payment, verify_data)

        assert Enrollment.objects.filter(user=user, course=course).count() == 1

    def test_coupon_usage_increments_exactly_once(self, user, course):
        coupon = Coupon.objects.create(code="ONCE", discount_type=Coupon.DiscountType.PERCENT, value=10)
        payment = Payment.objects.create(
            user=user, course=course, reference="XDA-test-once",
            amount_kobo=compute_amount_kobo(course, coupon), coupon=coupon,
        )
        verify_data = verify_response(reference=payment.reference, amount=payment.amount_kobo)["data"]

        grant_access(payment, verify_data)
        payment.refresh_from_db()
        grant_access(payment, verify_data)  # idempotent second call

        coupon.refresh_from_db()
        assert coupon.times_used == 1

    @pytest.mark.django_db(transaction=True)
    def test_concurrent_grant_access_creates_exactly_one_enrollment(self, user, course):
        """Addendum §6: "Return handler and reconciliation task racing
        on the same reference create exactly one Enrollment (simulate
        with a lock or a threaded test)." — the one people skip.

        Needs transaction=True: the default django_db fixture wraps a
        test in one uncommitted transaction on the main thread's
        connection, which SQLite's single-writer file lock then blocks
        every other thread's own connection from touching at all —
        that's a pytest-django/SQLite testing artifact, not something
        this test is meant to exercise. transaction=True makes the
        fixture actually commit, so separate threads' separate
        connections interact the way separate requests really would.
        """
        payment = make_payment(user, course)
        verify_data = verify_response(reference=payment.reference, amount=payment.amount_kobo)["data"]

        errors = []

        def run():
            from django.db import connection
            from django.db.utils import OperationalError
            # SQLite has no real row-level locking, so a burst of true
            # concurrent writers can hit "database is locked" purely
            # from single-writer file contention — Postgres (prod)
            # would just serialize these via select_for_update() and
            # block, not error. A bounded retry here is what a real
            # caller does too (see addendum §2.4 on reconciliation:
            # "exception rolls back the whole thing and ... retries
            # ... that is the correct behaviour"). If grant_access
            # itself is broken, retrying won't fix a wrong *result* —
            # only transient lock contention.
            for attempt in range(5):
                try:
                    grant_access(Payment.objects.get(pk=payment.pk), verify_data)
                    return
                except OperationalError as exc:
                    if attempt == 4:
                        errors.append(exc)
                    else:
                        time.sleep(0.05 * (attempt + 1))
                except Exception as exc:  # noqa: BLE001 — a non-lock error is a real failure
                    errors.append(exc)
                    return
                finally:
                    connection.close()

        threads = [threading.Thread(target=run) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"grant_access raised under concurrency: {errors}"
        assert Enrollment.objects.filter(user=user, course=course).count() == 1
        assert Payment.objects.get(pk=payment.pk).status == Payment.Status.SUCCESS


@pytest.mark.django_db
class TestReconciliation:
    def test_stale_pending_that_succeeded_is_picked_up_and_granted(self, user, course):
        """Addendum §6: "A PENDING payment older than 5 minutes that
        succeeded on Paystack is picked up by reconciliation and
        granted." """
        payment = make_payment(user, course)
        payment.initialized_at = timezone.now() - timezone.timedelta(minutes=10)
        payment.save(update_fields=["initialized_at"])

        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(reference=payment.reference, amount=payment.amount_kobo)
            result = reconcile_pending_payments()

        assert result["granted"] == 1
        assert Enrollment.objects.filter(user=user, course=course).exists()

    def test_payment_younger_than_5_minutes_not_touched(self, user, course):
        payment = make_payment(user, course)  # just created, well within 5 minutes
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            result = reconcile_pending_payments()
            mock_verify.assert_not_called()
        assert result["checked"] == 0

    def test_payment_older_than_7_days_marked_abandoned(self, user, course):
        payment = make_payment(user, course)
        payment.initialized_at = timezone.now() - timezone.timedelta(days=8)
        payment.save(update_fields=["initialized_at"])

        result = reconcile_pending_payments()
        payment.refresh_from_db()
        assert payment.status == Payment.Status.ABANDONED
        assert result["abandoned"] == 1


@pytest.mark.django_db
class TestSweep:
    def test_ignores_non_academy_references_entirely(self, user, course):
        """Addendum §6: "sweep_paystack_transactions ignores non-XDA-
        references entirely." """
        with patch("apps.payments.services.PaystackGateway.list_transactions") as mock_list:
            mock_list.return_value = {
                "status": True,
                "data": [
                    {"reference": "VET-something-unrelated", "amount": 100000, "metadata": {}},
                ],
                "meta": {"total": 1},
            }
            result = sweep_paystack_transactions()

        assert result["seen"] == 0
        assert result["flagged"] == 0
        from apps.operations.models import Signal
        assert Signal.objects.filter(key="payment.reconcile_mismatch").count() == 0

    def test_flags_academy_success_with_no_local_match(self, user, course):
        """Since Phase 11, this raises a real operations.Signal
        (payment.reconcile_mismatch) instead of the old
        ReconciliationFlag stand-in — see apps.payments.models.Payment
        and apps.operations.rules.payment_reconcile_mismatch."""
        with patch("apps.payments.services.PaystackGateway.list_transactions") as mock_list:
            mock_list.return_value = {
                "status": True,
                "data": [
                    {"reference": "XDA-orphaned-transaction", "amount": 4_500_000,
                     "metadata": {"product": "xpress_academy"}, "paid_at": "2026-08-01T00:00:00Z"},
                ],
                "meta": {"total": 1},
            }
            result = sweep_paystack_transactions()

        assert result["seen"] == 1
        assert result["flagged"] == 1
        from apps.operations.models import Signal
        signal = Signal.objects.get(key="payment.reconcile_mismatch", dedupe_key="payment.reconcile_mismatch:XDA-orphaned-transaction")
        assert signal.severity == Signal.Severity.CRITICAL
        assert signal.status == Signal.Status.OPEN

    def test_does_not_flag_when_local_success_exists(self, user, course):
        payment = make_payment(user, course)
        payment.status = Payment.Status.SUCCESS
        payment.save(update_fields=["status"])

        with patch("apps.payments.services.PaystackGateway.list_transactions") as mock_list:
            mock_list.return_value = {
                "status": True,
                "data": [{"reference": payment.reference, "amount": payment.amount_kobo, "metadata": {"product": "xpress_academy"}}],
                "meta": {"total": 1},
            }
            result = sweep_paystack_transactions()

        assert result["flagged"] == 0


@pytest.mark.django_db
class TestRefund:
    def test_refund_never_calls_paystack_api(self, user, course):
        payment = make_payment(user, course)
        payment.status = Payment.Status.SUCCESS
        payment.save(update_fields=["status"])

        with patch("apps.payments.gateway.requests.request") as mock_request:
            from .services import refund_payment
            refund_payment(payment, reason="test refund")
            mock_request.assert_not_called()

        payment.refresh_from_db()
        assert payment.status == Payment.Status.REFUNDED
        assert payment.refunded_at is not None


@pytest.mark.django_db
class TestCheckoutViews:
    def test_checkout_requires_login(self, course):
        client = Client()
        resp = client.get(f"/checkout/{course.slug}/")
        assert resp.status_code == 302
        assert "/account/login/" in resp["Location"]

    def test_already_enrolled_redirects_to_curriculum(self, user, course):
        Enrollment.objects.create(user=user, course=course)
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{course.slug}/")
        assert resp.status_code == 302
        assert resp["Location"].endswith(f"/learn/{course.slug}/")

    def test_return_handler_no_reference_shows_error_not_500(self):
        client = Client()
        resp = client.get("/checkout/return/")
        assert resp.status_code == 200
        assert b"payment reference" in resp.content.lower()

    def test_return_handler_grants_and_redirects_on_success(self, user, course):
        payment = make_payment(user, course)
        client = Client()
        client.force_login(user)
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(reference=payment.reference, amount=payment.amount_kobo)
            resp = client.get(f"/checkout/return/?reference={payment.reference}")
        assert resp.status_code == 302
        assert Enrollment.objects.filter(user=user, course=course).exists()


@pytest.mark.django_db
class TestReferralCapture:
    def test_ref_param_stored_and_attributed_on_checkout(self, user, course):
        partner = Partner.objects.create(name="Test Clinic", referral_code="testclinic")
        client = Client()
        client.force_login(user)
        client.get(f"/checkout/{course.slug}/?ref=testclinic")  # captures into session

        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            client.post(f"/checkout/{course.slug}/")

        payment = Payment.objects.get(user=user, course=course)
        assert payment.partner_id == partner.id

    def test_unknown_ref_code_not_stored(self, user, course):
        client = Client()
        client.force_login(user)
        client.get(f"/checkout/{course.slug}/?ref=doesnotexist")

        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            client.post(f"/checkout/{course.slug}/")

        payment = Payment.objects.get(user=user, course=course)
        assert payment.partner_id is None


@pytest.mark.django_db
class TestPricingModels:
    def test_free_course_grants_access_with_no_payment(self, user, course):
        course.pricing_model = Course.PricingModel.FREE
        course.save(update_fields=["pricing_model"])
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{course.slug}/")
        assert resp.status_code == 302
        assert Enrollment.objects.filter(user=user, course=course).exists()
        assert Payment.objects.filter(user=user, course=course).count() == 0

    def test_certificate_paid_course_grants_free_access(self, user, course):
        course.pricing_model = Course.PricingModel.CERTIFICATE_PAID
        course.save(update_fields=["pricing_model"])
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{course.slug}/")
        assert resp.status_code == 302
        assert Enrollment.objects.filter(user=user, course=course).exists()
        assert Payment.objects.filter(user=user, course=course).count() == 0

    def test_pay_what_you_want_below_minimum_rejected(self, user, course):
        course.pricing_model = Course.PricingModel.PAY_WHAT_YOU_WANT
        course.minimum_price_ngn = 1000
        course.save(update_fields=["pricing_model", "minimum_price_ngn"])
        client = Client()
        client.force_login(user)
        resp = client.post(f"/checkout/{course.slug}/", {"amount_ngn": "500"})
        assert resp.status_code == 200
        assert b"least" in resp.content
        assert not Enrollment.objects.filter(user=user, course=course).exists()

    def test_pay_what_you_want_zero_with_zero_minimum_is_free(self, user, course):
        course.pricing_model = Course.PricingModel.PAY_WHAT_YOU_WANT
        course.minimum_price_ngn = 0
        course.save(update_fields=["pricing_model", "minimum_price_ngn"])
        client = Client()
        client.force_login(user)
        resp = client.post(f"/checkout/{course.slug}/", {"amount_ngn": "0"})
        assert resp.status_code == 302
        assert Enrollment.objects.filter(user=user, course=course).exists()
        assert Payment.objects.filter(user=user, course=course).count() == 0

    def test_pay_what_you_want_uses_custom_amount(self, user, course):
        course.pricing_model = Course.PricingModel.PAY_WHAT_YOU_WANT
        course.minimum_price_ngn = 1000
        course.save(update_fields=["pricing_model", "minimum_price_ngn"])
        client = Client()
        client.force_login(user)
        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            client.post(f"/checkout/{course.slug}/", {"amount_ngn": "7000"})
        payment = Payment.objects.get(user=user, course=course)
        assert payment.amount_kobo == 700_000

    def test_certificate_checkout_requires_completion(self, user, course):
        course.pricing_model = Course.PricingModel.CERTIFICATE_PAID
        course.save(update_fields=["pricing_model"])
        Enrollment.objects.create(user=user, course=course)  # not completed
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{course.slug}/certificate/")
        assert resp.status_code == 302
        assert "curriculum" in resp["Location"] or f"/learn/{course.slug}/" in resp["Location"]

    def test_certificate_checkout_and_payment_issues_certificate(self, user, course):
        from apps.catalog.models import Lesson, Module
        from apps.certificates.models import Certificate
        from apps.enrollment.services import mark_lesson_complete

        course.pricing_model = Course.PricingModel.CERTIFICATE_PAID
        course.price_ngn = 2000
        course.save(update_fields=["pricing_model", "price_ngn"])
        module = Module.objects.create(course=course, order=1, title="M1")
        Lesson.objects.create(module=module, order=1, title="L1", type=Lesson.Type.TEXT)
        enrollment = Enrollment.objects.create(user=user, course=course)
        mark_lesson_complete(enrollment, module.lessons.first())
        assert Certificate.objects.filter(enrollment=enrollment).count() == 0

        client = Client()
        client.force_login(user)
        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            client.post(f"/checkout/{course.slug}/certificate/")
        payment = Payment.objects.get(user=user, course=course, purpose=Payment.Purpose.CERTIFICATE)

        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = verify_response(reference=payment.reference, amount=payment.amount_kobo)
            resp = client.get(f"/checkout/return/?reference={payment.reference}")

        assert resp.status_code == 302
        assert Certificate.objects.filter(enrollment=enrollment).count() == 1


@pytest.mark.django_db
class TestCoursePrerequisite:
    def test_checkout_blocked_without_prerequisite_completed(self, user, course, org):
        from apps.catalog.models import Programme

        programme = course.programme
        advanced = Course.objects.create(
            organization=org, programme=programme, title="Advanced Course", audience=Audience.BREEDER,
            price_ngn=5000, prerequisite=course,
        )
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{advanced.slug}/")
        assert resp.status_code == 302
        assert resp["Location"].endswith(f"/courses/{course.slug}/")
        assert not Enrollment.objects.filter(user=user, course=advanced).exists()

    def test_checkout_allowed_once_prerequisite_completed(self, user, course, org):
        advanced = Course.objects.create(
            organization=org, programme=course.programme, title="Advanced Course", audience=Audience.BREEDER,
            pricing_model=Course.PricingModel.FREE, prerequisite=course,
        )
        Enrollment.objects.create(user=user, course=course, status=Enrollment.Status.COMPLETED)
        client = Client()
        client.force_login(user)
        resp = client.get(f"/checkout/{advanced.slug}/")
        assert resp.status_code == 302
        assert Enrollment.objects.filter(user=user, course=advanced).exists()
