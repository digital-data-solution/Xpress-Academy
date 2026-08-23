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
