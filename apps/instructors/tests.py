import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Audience, Course, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization
from apps.payments.models import Payment

from .models import CourseReview, EarningsEntry, Instructor, Payout, Vertical
from .services import (
    complete_review,
    determine_attribution,
    generate_payout,
    get_instructor_balance,
    mark_payout_sent,
    record_sale_earnings,
    reverse_earnings_for_refund,
    submit_course_for_review,
)


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def reviewer(org):
    return User.objects.create_user(email="reviewer@example.com", password="testpass123")


@pytest.fixture
def vertical(org, reviewer):
    return Vertical.objects.create(organization=org, name="Test Vertical", domain_reviewer=reviewer)


@pytest.fixture
def instructor_user():
    return User.objects.create_user(email="instructor@example.com", password="testpass123")


@pytest.fixture
def instructor(org, instructor_user):
    return Instructor.objects.create(
        organization=org, user=instructor_user, display_name="Test Instructor",
        verification_status=Instructor.VerificationStatus.VERIFIED, agreement_signed_at=timezone.now(),
        own_traffic_rate=70, platform_traffic_rate=50,
    )


@pytest.fixture
def instructor_course(org, vertical, instructor):
    programme = Programme.objects.create(organization=org, title="P", audience=Audience.BREEDER)
    return Course.objects.create(
        organization=org, programme=programme, title="Instructor Course", audience=Audience.BREEDER,
        price_ngn=10000, instructor=instructor, vertical=vertical,
    )


@pytest.mark.django_db
class TestInstructorEligibility:
    def test_unverified_instructor_not_eligible(self, org, instructor_user):
        instructor = Instructor.objects.create(organization=org, user=instructor_user, display_name="X")
        assert instructor.is_eligible_for_courses is False

    def test_verified_but_no_agreement_not_eligible(self, org, instructor_user):
        instructor = Instructor.objects.create(
            organization=org, user=instructor_user, display_name="X",
            verification_status=Instructor.VerificationStatus.VERIFIED,
        )
        assert instructor.is_eligible_for_courses is False

    def test_verified_and_signed_is_eligible(self, instructor):
        assert instructor.is_eligible_for_courses is True

    def test_referral_code_auto_generated_and_unique(self, org, instructor_user):
        i1 = Instructor.objects.create(organization=org, user=instructor_user, display_name="Same Name")
        u2 = User.objects.create_user(email="second@example.com", password="testpass123")
        i2 = Instructor.objects.create(organization=org, user=u2, display_name="Same Name")
        assert i1.referral_code != i2.referral_code


@pytest.mark.django_db
class TestReviewWorkflowAppendOnly:
    def test_submit_creates_round_1(self, instructor_course, instructor_user):
        review = submit_course_for_review(instructor_course, submitted_by=instructor_user)
        assert review.round == 1
        instructor_course.refresh_from_db()
        assert instructor_course.review_status == Course.ReviewStatus.SUBMITTED

    def test_second_submission_creates_round_2_not_overwrite(self, instructor_course, instructor_user, reviewer):
        r1 = submit_course_for_review(instructor_course, submitted_by=instructor_user)
        complete_review(r1, CourseReview.Outcome.CHANGES_REQUESTED, reviewer, notes_to_instructor="fix X")
        r2 = submit_course_for_review(instructor_course, submitted_by=instructor_user)
        assert r2.round == 2
        assert CourseReview.objects.filter(course=instructor_course).count() == 2
        r1.refresh_from_db()
        assert r1.outcome == CourseReview.Outcome.CHANGES_REQUESTED  # untouched by round 2

    def test_approval_sets_course_approved(self, instructor_course, instructor_user, reviewer):
        review = submit_course_for_review(instructor_course, submitted_by=instructor_user)
        complete_review(review, CourseReview.Outcome.APPROVED, reviewer)
        instructor_course.refresh_from_db()
        assert instructor_course.review_status == Course.ReviewStatus.APPROVED
        assert instructor_course.reviewed_by == reviewer


@pytest.mark.django_db
class TestEarningsLedger:
    def test_first_party_course_no_earnings(self, org, vertical):
        programme = Programme.objects.create(organization=org, title="P", audience=Audience.BREEDER)
        course = Course.objects.create(
            organization=org, programme=programme, title="First Party", audience=Audience.BREEDER,
            price_ngn=10000, instructor=None,
        )
        user = User.objects.create_user(email="buyer@example.com", password="testpass123")
        payment = Payment.objects.create(user=user, course=course, reference="XDA-fp-1", amount_kobo=1_000_000, attribution=Payment.Attribution.PLATFORM_TRAFFIC)
        assert record_sale_earnings(payment) == []

    def test_own_traffic_uses_own_rate(self, instructor, instructor_course):
        user = User.objects.create_user(email="buyer2@example.com", password="testpass123")
        payment = Payment.objects.create(
            user=user, course=instructor_course, reference="XDA-own-1", amount_kobo=1_000_000,
            attribution=Payment.Attribution.OWN_TRAFFIC,
        )
        entries = record_sale_earnings(payment)
        assert len(entries) == 3
        earning = next(e for e in entries if e.entry_type == EarningsEntry.EntryType.INSTRUCTOR_EARNING)
        assert earning.amount_kobo == 700_000  # 70% of 1,000,000
        assert earning.rate_applied == 70

    def test_platform_traffic_uses_platform_rate(self, instructor, instructor_course):
        user = User.objects.create_user(email="buyer3@example.com", password="testpass123")
        payment = Payment.objects.create(
            user=user, course=instructor_course, reference="XDA-plat-1", amount_kobo=1_000_000,
            attribution=Payment.Attribution.PLATFORM_TRAFFIC,
        )
        entries = record_sale_earnings(payment)
        earning = next(e for e in entries if e.entry_type == EarningsEntry.EntryType.INSTRUCTOR_EARNING)
        assert earning.amount_kobo == 500_000  # 50%

    def test_balance_is_computed_not_stored(self, instructor, instructor_course):
        user = User.objects.create_user(email="buyer4@example.com", password="testpass123")
        payment = Payment.objects.create(
            user=user, course=instructor_course, reference="XDA-bal-1", amount_kobo=1_000_000,
            attribution=Payment.Attribution.PLATFORM_TRAFFIC,
        )
        record_sale_earnings(payment)
        assert get_instructor_balance(instructor) == 500_000

    def test_record_sale_earnings_idempotent(self, instructor, instructor_course):
        user = User.objects.create_user(email="buyer5@example.com", password="testpass123")
        payment = Payment.objects.create(
            user=user, course=instructor_course, reference="XDA-idem-1", amount_kobo=1_000_000,
            attribution=Payment.Attribution.PLATFORM_TRAFFIC,
        )
        record_sale_earnings(payment)
        record_sale_earnings(payment)
        assert EarningsEntry.objects.filter(payment=payment, entry_type=EarningsEntry.EntryType.SALE_GROSS).count() == 1

    def test_refund_reverses_instructor_earning_only(self, instructor, instructor_course):
        user = User.objects.create_user(email="buyer6@example.com", password="testpass123")
        payment = Payment.objects.create(
            user=user, course=instructor_course, reference="XDA-refund-1", amount_kobo=1_000_000,
            attribution=Payment.Attribution.PLATFORM_TRAFFIC,
        )
        record_sale_earnings(payment)
        balance_before = get_instructor_balance(instructor)
        reverse_earnings_for_refund(payment)
        balance_after = get_instructor_balance(instructor)
        assert balance_after == 0
        assert balance_before == 500_000


@pytest.mark.django_db
class TestPayout:
    def test_generate_and_mark_sent(self, instructor, instructor_course):
        user = User.objects.create_user(email="buyer7@example.com", password="testpass123")
        payment = Payment.objects.create(
            user=user, course=instructor_course, reference="XDA-payout-1", amount_kobo=1_000_000,
            attribution=Payment.Attribution.PLATFORM_TRAFFIC,
        )
        record_sale_earnings(payment)

        today = timezone.now().date()
        payout = generate_payout(instructor, today, today)
        assert payout.status == Payout.Status.DRAFT
        assert payout.amount_kobo == 500_000

        mark_payout_sent(payout, bank_reference="TEST-REF-123")
        payout.refresh_from_db()
        assert payout.status == Payout.Status.SENT
        assert get_instructor_balance(instructor) == 0  # PAYOUT_SENT entry zeroes it out


@pytest.mark.django_db
class TestAttribution:
    def test_no_referral_direct_sale_platform_traffic(self, instructor_course, rf):
        request = rf.get("/checkout/")
        request.session = {}
        attribution, attributed_instructor, source = determine_attribution(request, instructor_course)
        assert attribution == Payment.Attribution.PLATFORM_TRAFFIC
        assert attributed_instructor is None

    def test_own_referral_link_within_window(self, instructor, instructor_course, rf):
        request = rf.get("/checkout/")
        request.session = {
            "instructor_ref": {
                "code": instructor.referral_code,
                "expires": (timezone.now() + timezone.timedelta(days=10)).isoformat(),
            }
        }
        attribution, attributed_instructor, source = determine_attribution(request, instructor_course)
        assert attribution == Payment.Attribution.OWN_TRAFFIC
        assert attributed_instructor == instructor

    def test_expired_referral_ignored(self, instructor, instructor_course, rf):
        request = rf.get("/checkout/")
        request.session = {
            "instructor_ref": {
                "code": instructor.referral_code,
                "expires": (timezone.now() - timezone.timedelta(days=1)).isoformat(),
            }
        }
        attribution, attributed_instructor, source = determine_attribution(request, instructor_course)
        assert attribution == Payment.Attribution.PLATFORM_TRAFFIC
        assert attributed_instructor is None

    def test_other_instructors_referral_is_platform_traffic(self, org, vertical, instructor_course, rf):
        other_user = User.objects.create_user(email="other-instructor@example.com", password="testpass123")
        other = Instructor.objects.create(organization=org, user=other_user, display_name="Other")
        request = rf.get("/checkout/")
        request.session = {
            "instructor_ref": {"code": other.referral_code, "expires": (timezone.now() + timezone.timedelta(days=10)).isoformat()}
        }
        attribution, attributed_instructor, source = determine_attribution(request, instructor_course)
        assert attribution == Payment.Attribution.PLATFORM_TRAFFIC
        assert attributed_instructor == other  # referral is tracked even though it's not their own course


@pytest.mark.django_db
class TestTeachViews:
    def test_apply_requires_login(self):
        resp = Client().get("/teach/apply/")
        assert resp.status_code == 302

    def test_dashboard_redirects_non_instructor_to_apply(self):
        user = User.objects.create_user(email="plain@example.com", password="testpass123")
        client = Client()
        client.force_login(user)
        resp = client.get("/teach/dashboard/")
        assert resp.status_code == 302
        assert "/teach/apply/" in resp["Location"]

    def test_instructor_can_reach_dashboard(self, instructor, instructor_user):
        client = Client()
        client.force_login(instructor_user)
        resp = client.get("/teach/dashboard/")
        assert resp.status_code == 200

    def test_learners_page_never_shows_email(self, instructor, instructor_course, instructor_user):
        learner = User.objects.create_user(email="secret-email@example.com", password="testpass123", first_name="Ada")
        Enrollment.objects.create(user=learner, course=instructor_course)
        client = Client()
        client.force_login(instructor_user)
        resp = client.get(f"/teach/courses/{instructor_course.slug}/learners/")
        assert resp.status_code == 200
        assert b"secret-email@example.com" not in resp.content
        assert b"Ada" in resp.content

    def test_instructor_cannot_see_another_instructors_course(self, org, vertical, instructor, instructor_user):
        other_user = User.objects.create_user(email="other2@example.com", password="testpass123")
        other = Instructor.objects.create(
            organization=org, user=other_user, display_name="Other Instructor",
            verification_status=Instructor.VerificationStatus.VERIFIED, agreement_signed_at=timezone.now(),
        )
        programme = Programme.objects.create(organization=org, title="P2", audience=Audience.BREEDER)
        other_course = Course.objects.create(
            organization=org, programme=programme, title="Other's Course", audience=Audience.BREEDER,
            price_ngn=5000, instructor=other, vertical=vertical,
        )
        client = Client()
        client.force_login(instructor_user)  # logged in as `instructor`, not `other`
        resp = client.get(f"/teach/courses/{other_course.slug}/edit/")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestEndToEndCheckoutWiring:
    """Proves the gap flagged after the initial Phase 10 build is
    actually closed: a real checkout against an instructor-owned
    course creates EarningsEntry rows, not just the standalone
    service functions in isolation."""

    def test_checkout_creates_earnings_entries(self, instructor, instructor_course):
        from unittest.mock import patch

        buyer = User.objects.create_user(email="e2e-buyer@example.com", password="testpass123")
        buyer.profile.email_verified = True
        buyer.profile.save(update_fields=["email_verified"])

        client = Client()
        client.force_login(buyer)

        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            client.post(f"/checkout/{instructor_course.slug}/")

        payment = Payment.objects.get(user=buyer, course=instructor_course)
        assert payment.attribution == Payment.Attribution.PLATFORM_TRAFFIC  # no referral link used

        verify_data = {
            "status": "success", "amount": payment.amount_kobo, "currency": "NGN",
            "reference": payment.reference, "metadata": {"product": "xpress_academy"},
        }
        with patch("apps.payments.services.PaystackGateway.verify_transaction") as mock_verify:
            mock_verify.return_value = {"status": True, "data": verify_data}
            client.get(f"/checkout/return/?reference={payment.reference}")

        assert EarningsEntry.objects.filter(payment=payment, entry_type=EarningsEntry.EntryType.INSTRUCTOR_EARNING).exists()
        assert get_instructor_balance(instructor) == 500_000  # 50% platform-traffic rate

    def test_checkout_with_referral_link_attributes_own_traffic(self, instructor, instructor_course):
        from unittest.mock import patch

        buyer = User.objects.create_user(email="e2e-buyer2@example.com", password="testpass123")
        buyer.profile.email_verified = True
        buyer.profile.save(update_fields=["email_verified"])

        client = Client()
        client.force_login(buyer)
        client.get(f"/courses/{instructor_course.slug}/?ref={instructor.referral_code}")  # captures the referral

        with patch("apps.payments.services.PaystackGateway.initialize_transaction") as mock_init:
            mock_init.return_value = {"status": True, "data": {"authorization_url": "https://paystack.test/pay/x"}}
            client.post(f"/checkout/{instructor_course.slug}/")

        payment = Payment.objects.get(user=buyer, course=instructor_course)
        assert payment.attribution == Payment.Attribution.OWN_TRAFFIC
        assert payment.attributed_instructor == instructor
