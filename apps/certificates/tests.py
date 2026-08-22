"""Coverage required by build spec §11 before Hard Stop 2:
"Completion → certificate — including the negative case (final not passed)."
"""

import pytest
from django.test import Client

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.assessment.services import finalize_attempt, save_answer, start_attempt
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.enrollment.services import mark_lesson_complete
from apps.organizations.models import Organization

from .models import Certificate
from .pdf import CERTIFICATE_WORDING, FORBIDDEN_WORDS, build_certificate_pdf
from .services import issue_certificate, next_serial, revoke_certificate


@pytest.fixture
def org():
    return Organization.objects.create(
        name="Test Org", from_email="test@example.com",
        certificate_signatory_name="Dr. Test Signatory",
        certificate_signatory_title="Director",
    )


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience=Audience.BREEDER)
    return Course.objects.create(organization=org, programme=programme, title="Test Course", audience=Audience.BREEDER)


@pytest.fixture
def user():
    return User.objects.create_user(email="learner@example.com", password="testpass123", first_name="Ada", last_name="Learner")


@pytest.fixture
def enrollment(course, user):
    return Enrollment.objects.create(user=user, course=course)


def make_module_with_lesson(course, order=1):
    module = Module.objects.create(course=course, order=order, title=f"Module {order}")
    Lesson.objects.create(module=module, order=1, title=f"Lesson {order}.1", type=Lesson.Type.TEXT)
    return module


@pytest.mark.django_db
class TestCertificateIssuance:
    def test_no_final_assessment_issues_on_last_lesson(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.filter(enrollment=enrollment).first()
        assert cert is not None
        assert cert.learner_name_snapshot == "Ada Learner"
        assert cert.course_title_snapshot == course.title
        assert cert.final_score is None

    def test_final_assessment_required_but_not_passed_issues_nothing(self, org, course, enrollment):
        """The negative case §11 explicitly asks for."""
        course.requires_final_assessment = True
        course.save(update_fields=["requires_final_assessment"])
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())

        assert Certificate.objects.filter(enrollment=enrollment).count() == 0
        assert issue_certificate(enrollment) is None

    def test_final_assessment_passed_issues_certificate_with_score(self, org, course, enrollment):
        course.requires_final_assessment = True
        course.save(update_fields=["requires_final_assessment"])
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())

        bank = QuestionBank.objects.create(organization=org, name="Bank")
        q = Question.objects.create(bank=bank, type=Question.Type.MCQ, stem="Q1")
        Choice.objects.create(question=q, text="Right", is_correct=True, order=1)
        Choice.objects.create(question=q, text="Wrong", is_correct=False, order=2)
        quiz = Quiz.objects.create(scope=Quiz.Scope.FINAL, course=course, title="Final", bank=bank, question_count=1)

        attempt = start_attempt(enrollment, quiz)
        correct_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if c["is_correct"])
        save_answer(attempt, q.id, [correct_id])
        finalize_attempt(attempt)  # this is what triggers issuance via _mark_enrollment_completed_if_ready

        cert = Certificate.objects.get(enrollment=enrollment)
        assert cert.final_score == 100

    def test_issuance_is_idempotent(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        first = Certificate.objects.get(enrollment=enrollment)
        again = issue_certificate(enrollment)
        assert again.id == first.id
        assert Certificate.objects.filter(enrollment=enrollment).count() == 1

    def test_incomplete_course_issues_nothing(self, course, enrollment):
        make_module_with_lesson(course)
        make_module_with_lesson(course, order=2)
        # only complete module 1's lesson — course not done
        m1 = course.modules.get(order=1)
        mark_lesson_complete(enrollment, m1.lessons.first())
        assert issue_certificate(enrollment) is None
        assert Certificate.objects.filter(enrollment=enrollment).count() == 0

    def test_serial_format_and_sequencing(self, course, org):
        s1 = next_serial(course)
        s2 = next_serial(course)
        assert s1.startswith("XDA-BRD-")
        assert s1 != s2
        n1 = int(s1.rsplit("-", 1)[1])
        n2 = int(s2.rsplit("-", 1)[1])
        assert n2 == n1 + 1

    def test_revoke_certificate(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)
        revoke_certificate(cert, "test reason")
        cert.refresh_from_db()
        assert cert.is_revoked is True
        assert cert.revoked_reason == "test reason"
        assert cert.revoked_at is not None


@pytest.mark.django_db
class TestCertificateWording:
    def test_required_wording_present_and_forbidden_words_absent(self):
        for word in FORBIDDEN_WORDS:
            assert word not in CERTIFICATE_WORDING
        assert "Xpress Digital Academy" in CERTIFICATE_WORDING
        assert "RC 9112280" in CERTIFICATE_WORDING
        assert "Certificate of Completion" in CERTIFICATE_WORDING

    def test_pdf_actually_generates(self, course, enrollment, org):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)
        pdf_bytes = build_certificate_pdf(cert)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 500
        # certificate.pdf field should already be populated by issuance
        assert cert.pdf.name


@pytest.mark.django_db
class TestVerificationViews:
    def test_valid_certificate_shows_details(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)

        client = Client()
        resp = client.get(f"/verify/{cert.verification_slug}/")
        assert resp.status_code == 200
        assert b"Ada Learner" in resp.content
        assert cert.serial.encode() in resp.content

    def test_revoked_certificate_shows_revoked_not_details(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)
        revoke_certificate(cert, "fraud")

        client = Client()
        resp = client.get(f"/verify/{cert.verification_slug}/")
        assert resp.status_code == 200
        assert b"revoked" in resp.content.lower()

    def test_unknown_slug_shows_not_found_not_500(self):
        import uuid
        client = Client()
        resp = client.get(f"/verify/{uuid.uuid4()}/")
        assert resp.status_code == 200
        assert b"No certificate found" in resp.content

    def test_owner_can_view_own_certificate(self, course, enrollment, user):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)

        client = Client()
        client.force_login(user)
        resp = client.get(f"/certificates/{cert.serial}/")
        assert resp.status_code == 200

    def test_other_user_cannot_view_someone_elses_certificate(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)

        other = User.objects.create_user(email="other@example.com", password="testpass123")
        client = Client()
        client.force_login(other)
        resp = client.get(f"/certificates/{cert.serial}/")
        assert resp.status_code == 404

    def test_anonymous_cannot_view_own_certificate_page(self, course, enrollment):
        m1 = make_module_with_lesson(course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        cert = Certificate.objects.get(enrollment=enrollment)

        client = Client()
        resp = client.get(f"/certificates/{cert.serial}/")
        assert resp.status_code == 302
