"""Phase 8 — public site. Catalog/accounts/organizations had no tests
before this (noted in README as thin, revisit when they grow real
logic) — the public views are exactly that growth, so real coverage
starts here."""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

from .models import Audience, Course, CourseFAQ, Programme


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def published_course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience=Audience.BREEDER)
    return Course.objects.create(
        organization=org, programme=programme, title="Published Course", slug="published-course",
        audience=Audience.BREEDER, price_ngn=10000, is_published=True,
        review_status=Course.ReviewStatus.APPROVED,  # required since Phase 10's publication gate
    )


@pytest.fixture
def unpublished_course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme 2", audience=Audience.BREEDER)
    return Course.objects.create(
        organization=org, programme=programme, title="Draft Course", slug="draft-course",
        audience=Audience.BREEDER, price_ngn=10000, is_published=False,
    )


@pytest.mark.django_db
class TestLandingPage:
    def test_loads(self, org):
        resp = Client().get("/")
        assert resp.status_code == 200

    def test_shows_published_course(self, org, published_course):
        resp = Client().get("/")
        assert published_course.title.encode() in resp.content

    def test_hides_unpublished_course(self, org, unpublished_course):
        resp = Client().get("/")
        assert unpublished_course.title.encode() not in resp.content


@pytest.mark.django_db
class TestCourseCatalog:
    def test_loads_with_no_courses(self, org):
        resp = Client().get("/courses/")
        assert resp.status_code == 200

    def test_shows_published_only(self, org, published_course, unpublished_course):
        resp = Client().get("/courses/")
        assert published_course.title.encode() in resp.content
        assert unpublished_course.title.encode() not in resp.content


@pytest.mark.django_db
class TestCourseDetail:
    def test_published_course_loads(self, published_course):
        resp = Client().get(f"/courses/{published_course.slug}/")
        assert resp.status_code == 200
        assert published_course.title.encode() in resp.content

    def test_unpublished_course_404s(self, unpublished_course):
        resp = Client().get(f"/courses/{unpublished_course.slug}/")
        assert resp.status_code == 404

    def test_shows_faqs(self, published_course):
        CourseFAQ.objects.create(course=published_course, question="Is this real?", answer="Yes.", order=1)
        resp = Client().get(f"/courses/{published_course.slug}/")
        assert b"Is this real?" in resp.content

    def test_enroll_cta_for_anonymous(self, published_course):
        resp = Client().get(f"/courses/{published_course.slug}/")
        assert b"Enroll now" in resp.content

    def test_go_to_course_cta_for_enrolled_user(self, published_course):
        user = User.objects.create_user(email="learner@example.com", password="testpass123")
        Enrollment.objects.create(user=user, course=published_course)
        client = Client()
        client.force_login(user)
        resp = client.get(f"/courses/{published_course.slug}/")
        assert b"Go to course" in resp.content
        assert b"Enroll now" not in resp.content

    def test_sales_headline_used_when_set(self, published_course):
        published_course.sales_headline = "Custom Headline Here"
        published_course.save(update_fields=["sales_headline"])
        resp = Client().get(f"/courses/{published_course.slug}/")
        assert b"Custom Headline Here" in resp.content

    def test_falls_back_to_title_when_no_sales_headline(self, published_course):
        resp = Client().get(f"/courses/{published_course.slug}/")
        assert published_course.title.encode() in resp.content


@pytest.mark.django_db
class TestSEO:
    def test_sitemap_loads(self, published_course):
        resp = Client().get("/sitemap.xml")
        assert resp.status_code == 200
        assert b"published-course" in resp.content

    def test_sitemap_excludes_unpublished(self, unpublished_course):
        resp = Client().get("/sitemap.xml")
        assert b"draft-course" not in resp.content

    def test_robots_txt(self):
        resp = Client().get("/robots.txt")
        assert resp.status_code == 200
        assert b"Sitemap:" in resp.content


@pytest.mark.django_db
class TestErrorPages:
    def test_404_page_renders(self, settings):
        settings.DEBUG = False
        settings.ALLOWED_HOSTS = ["*"]
        resp = Client(raise_request_exception=False).get("/this-does-not-exist/")
        assert resp.status_code == 404
        assert b"Page not found" in resp.content


@pytest.mark.django_db
class TestPublicationGate:
    """Phase 10 build spec: "is_published cannot be True unless
    review_status == APPROVED. Enforce at the model level with a
    CheckConstraint or clean(). There must be no admin path, no
    management command, and no API route that publishes an unapproved
    course. Write a test that proves it." This is that test — it
    deliberately bypasses clean()/full_clean() to prove the DATABASE
    constraint holds even when application-level validation is
    skipped entirely, which is the actual bar the spec sets."""

    def test_clean_rejects_publish_without_approval(self, org):
        programme = Programme.objects.create(organization=org, title="P", audience=Audience.BREEDER)
        course = Course.objects.create(
            organization=org, programme=programme, title="Gate Test", audience=Audience.BREEDER,
            price_ngn=1000, is_published=False, review_status=Course.ReviewStatus.DRAFT,
        )
        course.is_published = True
        with pytest.raises(Exception):  # ValidationError from clean()
            course.full_clean()

    def test_raw_update_bypassing_clean_still_blocked_by_db_constraint(self, org):
        """The actual bypass attempt: skip clean()/full_clean()
        entirely via a bulk .update(), which is exactly how a
        forgotten API route or management command would fail to
        validate. The DB CheckConstraint must reject it regardless."""
        from django.db import IntegrityError, transaction

        programme = Programme.objects.create(organization=org, title="P2", audience=Audience.BREEDER)
        course = Course.objects.create(
            organization=org, programme=programme, title="Gate Test 2", audience=Audience.BREEDER,
            price_ngn=1000, is_published=False, review_status=Course.ReviewStatus.DRAFT,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Course.objects.filter(pk=course.pk).update(is_published=True)  # review_status still DRAFT

        course.refresh_from_db()
        assert course.is_published is False

    def test_approved_course_can_publish(self, org):
        from apps.instructors.models import Vertical

        reviewer = User.objects.create_user(email="reviewer3@example.com", password="testpass123")
        vertical = Vertical.objects.create(organization=org, name="Publishable Vertical", domain_reviewer=reviewer)
        programme = Programme.objects.create(organization=org, title="P3", audience=Audience.BREEDER)
        course = Course.objects.create(
            organization=org, programme=programme, title="Gate Test 3", audience=Audience.BREEDER,
            price_ngn=1000, is_published=False, review_status=Course.ReviewStatus.APPROVED, vertical=vertical,
        )
        course.is_published = True
        course.full_clean()  # does not raise
        course.save()
        assert Course.objects.get(pk=course.pk).is_published is True

    def test_cannot_approve_course_with_no_vertical(self, org):
        programme = Programme.objects.create(organization=org, title="P4", audience=Audience.BREEDER)
        course = Course.objects.create(
            organization=org, programme=programme, title="Gate Test 4", audience=Audience.BREEDER,
            price_ngn=1000, review_status=Course.ReviewStatus.APPROVED, vertical=None,
        )
        with pytest.raises(Exception):
            course.full_clean()

    def test_cannot_approve_course_in_vertical_with_no_domain_reviewer(self, org):
        from apps.instructors.models import Vertical

        programme = Programme.objects.create(organization=org, title="P5", audience=Audience.BREEDER)
        vertical = Vertical.objects.create(organization=org, name="No Reviewer Yet")
        course = Course.objects.create(
            organization=org, programme=programme, title="Gate Test 5", audience=Audience.BREEDER,
            price_ngn=1000, review_status=Course.ReviewStatus.APPROVED, vertical=vertical,
        )
        with pytest.raises(Exception):
            course.full_clean()

    def test_can_approve_course_with_vertical_and_reviewer(self, org):
        from apps.instructors.models import Vertical

        reviewer = User.objects.create_user(email="reviewer@example.com", password="testpass123")
        programme = Programme.objects.create(organization=org, title="P6", audience=Audience.BREEDER)
        vertical = Vertical.objects.create(organization=org, name="Has A Reviewer", domain_reviewer=reviewer)
        course = Course.objects.create(
            organization=org, programme=programme, title="Gate Test 6", audience=Audience.BREEDER,
            price_ngn=1000, review_status=Course.ReviewStatus.APPROVED, vertical=vertical,
        )
        course.full_clean()  # does not raise

    def test_instructor_must_be_verified_and_agreement_signed(self, org):
        from apps.instructors.models import Instructor

        applicant = User.objects.create_user(email="applicant@example.com", password="testpass123")
        instructor = Instructor.objects.create(
            organization=org, user=applicant, display_name="Applicant",
            verification_status=Instructor.VerificationStatus.UNVERIFIED,
        )
        programme = Programme.objects.create(organization=org, title="P7", audience=Audience.BREEDER)
        course = Course(
            organization=org, programme=programme, title="Gate Test 7", audience=Audience.BREEDER,
            price_ngn=1000, instructor=instructor,
        )
        with pytest.raises(Exception):
            course.full_clean()
