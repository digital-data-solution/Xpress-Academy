"""Coverage for build spec §B: bulk-enrolment (seat cap enforcement,
never overwriting an enrollment a student already has some other way,
the licence-not-active guard) and the free diagnostic mock test (grading,
topic breakdown, expiry, PDF generation, and the public HTTP flow)."""

import io
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, SourceExam, SyllabusTopic
from apps.catalog.models import Course, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

from .diagnostics import (
    finalize_diagnostic_attempt,
    generate_and_save_report_pdf,
    save_diagnostic_answer,
    start_diagnostic_attempt,
)
from .models import DiagnosticAttempt, DiagnosticMockTest, Institution, InstitutionalLicense
from .services import bulk_enroll_students_from_csv


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience="BREEDER")
    return Course.objects.create(organization=org, programme=programme, title="Test Course", audience="BREEDER")


@pytest.fixture
def proprietor():
    return User.objects.create_user(email="proprietor@example.com", password="testpass123")


@pytest.fixture
def institution(org, proprietor):
    return Institution.objects.create(organization=org, name="Test Academy", proprietor=proprietor)


@pytest.fixture
def license(institution, course):
    lic = InstitutionalLicense.objects.create(
        institution=institution, seats=2, status=InstitutionalLicense.Status.ACTIVE,
        term_starts_at=timezone.now(), term_ends_at=timezone.now() + timezone.timedelta(days=90),
    )
    lic.courses.set([course])
    return lic


def csv_file(rows: str):
    return io.BytesIO(rows.encode("utf-8"))


@pytest.mark.django_db
class TestBulkEnroll:
    def test_new_students_get_accounts_and_seats(self, license, course):
        with patch("apps.engagement.services.ResendGateway.send"):
            result = bulk_enroll_students_from_csv(
                license,
                csv_file("email,first_name,last_name\nstudent1@example.com,A,One\nstudent2@example.com,B,Two\n"),
            )
        assert result.created == 2
        assert not result.errors
        assert license.seats_used == 2
        assert license.seats_remaining == 0
        assert Enrollment.objects.filter(
            course=course, source=Enrollment.Source.INSTITUTIONAL, institutional_license=license
        ).count() == 2

    def test_seat_cap_enforced(self, license):
        with patch("apps.engagement.services.ResendGateway.send"):
            result = bulk_enroll_students_from_csv(
                license,
                csv_file(
                    "email\nstudent1@example.com\nstudent2@example.com\nstudent3@example.com\n"
                ),
            )
        assert result.created == 2  # only 2 seats on the licence
        assert license.seats_used == 2
        assert any("seat cap reached" in e for e in result.errors)

    def test_does_not_overwrite_an_existing_non_institutional_enrollment(self, license, course):
        existing_user = User.objects.create_user(email="already-enrolled@example.com", password="testpass123")
        original = Enrollment.objects.create(
            user=existing_user, course=course, source=Enrollment.Source.PURCHASE, expires_at=None,
        )

        with patch("apps.engagement.services.ResendGateway.send"):
            bulk_enroll_students_from_csv(license, csv_file("email\nalready-enrolled@example.com\n"))

        original.refresh_from_db()
        assert original.source == Enrollment.Source.PURCHASE, "must not be silently downgraded to institutional"
        assert original.expires_at is None, "must not lose their lifetime access"
        assert original.institutional_license_id is None

    def test_re_importing_the_same_student_is_a_no_op(self, license):
        with patch("apps.engagement.services.ResendGateway.send"):
            bulk_enroll_students_from_csv(license, csv_file("email\nstudent1@example.com\n"))
            result = bulk_enroll_students_from_csv(license, csv_file("email\nstudent1@example.com\n"))

        assert result.created == 0
        assert result.already_seated == 1
        assert license.seats_used == 1  # not double-counted

    def test_pending_license_refuses_import(self, institution, course):
        pending = InstitutionalLicense.objects.create(
            institution=institution, seats=5, status=InstitutionalLicense.Status.PENDING,
            term_starts_at=timezone.now(), term_ends_at=timezone.now() + timezone.timedelta(days=90),
        )
        pending.courses.set([course])

        result = bulk_enroll_students_from_csv(pending, csv_file("email\nstudent1@example.com\n"))
        assert result.created == 0
        assert Enrollment.objects.count() == 0
        assert any("not Active" in e for e in result.errors)


@pytest.fixture
def bank(org):
    return QuestionBank.objects.create(organization=org, name="Test Bank")


@pytest.fixture
def source_exam():
    return SourceExam.objects.create(code="jamb", name="JAMB UTME")


@pytest.fixture
def diagnostic_questions(bank, source_exam):
    """5 Ecology + 3 Genetics questions, one deliberately DISPUTED so
    the same is_publishable gating the real quiz engine uses is
    exercised here too — a diagnostic is exactly the kind of public,
    first-impression artefact where a wrong answer key would be worst."""
    ecology = SyllabusTopic.objects.create(source_exam=source_exam, subject="Biology", name="Ecology")
    genetics = SyllabusTopic.objects.create(source_exam=source_exam, subject="Biology", name="Genetics")

    def make(topic, correct_text, verification_status="VERIFIED"):
        q = Question.objects.create(
            bank=bank, type=Question.Type.MCQ, stem=f"Question about {topic.name} — {correct_text}",
            explanation="Because.", verification_status=verification_status,
        )
        Choice.objects.create(question=q, text=correct_text, is_correct=True, order=1)
        Choice.objects.create(question=q, text="Wrong", is_correct=False, order=2)
        q.syllabus_topics.set([topic])
        return q

    questions = [make(ecology, f"Ecology correct {i}") for i in range(5)]
    questions += [make(genetics, f"Genetics correct {i}") for i in range(3)]
    questions.append(make(ecology, "Disputed correct", verification_status="DISPUTED"))
    return {"ecology": ecology, "genetics": genetics, "questions": questions}


@pytest.fixture
def diagnostic_test(org, bank, diagnostic_questions):
    return DiagnosticMockTest.objects.create(
        organization=org, title="Free JAMB Biology Diagnostic", bank=bank,
        question_count=8, time_limit_minutes=30,
    )


@pytest.mark.django_db
class TestDiagnosticGrading:
    def test_disputed_question_never_enters_a_snapshot(self, diagnostic_test, diagnostic_questions):
        attempt = start_diagnostic_attempt(diagnostic_test, student_name="Ada")
        snapshot_ids = {q["question_id"] for q in attempt.question_snapshot}
        disputed_id = next(q.id for q in diagnostic_questions["questions"] if q.verification_status == "DISPUTED")
        assert disputed_id not in snapshot_ids
        # pool is 8 publishable questions, question_count=8 — every publishable one is used
        assert len(snapshot_ids) == 8

    def test_grading_and_topic_breakdown(self, diagnostic_test):
        attempt = start_diagnostic_attempt(diagnostic_test, student_name="Ada", school_name="Test High School")
        for sq in attempt.question_snapshot:
            correct_choice_id = next(c["choice_id"] for c in sq["choices"] if c["is_correct"])
            save_diagnostic_answer(attempt, sq["question_id"], [correct_choice_id])

        result = finalize_diagnostic_attempt(attempt)
        assert result.score_percent == 100
        assert result.submitted_at is not None
        total_in_breakdown = sum(v["total"] for v in result.topic_breakdown.values())
        assert total_in_breakdown == len(attempt.question_snapshot)
        for topic_stats in result.topic_breakdown.values():
            assert topic_stats["correct"] == topic_stats["total"]

    def test_unanswered_questions_count_as_incorrect_not_a_blocker(self, diagnostic_test):
        attempt = start_diagnostic_attempt(diagnostic_test, student_name="Ada")
        # answer nothing at all
        result = finalize_diagnostic_attempt(attempt)
        assert result.score_percent == 0
        assert result.submitted_at is not None

    def test_expired_attempt_auto_finalizes(self, diagnostic_test):
        from .diagnostics import expire_diagnostic_attempt_if_stale

        attempt = start_diagnostic_attempt(diagnostic_test, student_name="Ada")
        attempt.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        attempt.save(update_fields=["expires_at"])

        result = expire_diagnostic_attempt_if_stale(attempt)
        assert result.submitted_at is not None


@pytest.mark.django_db
class TestDiagnosticPDF:
    def test_report_pdf_is_generated_and_saved(self, diagnostic_test):
        attempt = start_diagnostic_attempt(diagnostic_test, student_name="Ada", school_name="Test High School")
        for sq in attempt.question_snapshot:
            correct_choice_id = next(c["choice_id"] for c in sq["choices"] if c["is_correct"])
            save_diagnostic_answer(attempt, sq["question_id"], [correct_choice_id])
        finalize_diagnostic_attempt(attempt)

        result = generate_and_save_report_pdf(attempt)
        assert result.report_pdf.name
        content = result.report_pdf.read()
        assert content.startswith(b"%PDF")
        assert len(content) > 500  # a real rendered document, not an empty/broken stub

    def test_school_summary_pdf_covers_multiple_students(self, diagnostic_test):
        from .pdf import build_school_summary_pdf

        for name in ["Ada", "Bayo"]:
            attempt = start_diagnostic_attempt(diagnostic_test, student_name=name, school_name="Test High School")
            finalize_diagnostic_attempt(attempt)  # unanswered — 0% is fine, just needs to be submitted

        attempts = diagnostic_test.attempts.filter(submitted_at__isnull=False)
        pdf_bytes = build_school_summary_pdf(diagnostic_test, attempts)
        assert pdf_bytes.startswith(b"%PDF")
        assert len(pdf_bytes) > 500


@pytest.mark.django_db
class TestDiagnosticHTTPFlow:
    """The public, unauthenticated flow end to end — no login, no
    enrollment, exactly as a prospect clicking a shared link would
    experience it."""

    def test_full_flow_anonymous(self, diagnostic_test):
        client = Client()

        intro_url = reverse("licensing:diagnostic_intro", kwargs={"test_slug": diagnostic_test.slug})
        resp = client.post(intro_url, {"student_name": "Ada", "school_name": "Test High"})
        assert resp.status_code == 302

        attempt = DiagnosticAttempt.objects.get(student_name="Ada")
        attempt_url = reverse(
            "licensing:diagnostic_attempt",
            kwargs={"test_slug": diagnostic_test.slug, "attempt_uuid": attempt.uuid},
        )
        resp = client.get(attempt_url)
        assert resp.status_code == 200

        # Submit every question correct via the same POST shape the real form uses.
        post_data = {}
        for sq in attempt.question_snapshot:
            correct_choice_id = next(c["choice_id"] for c in sq["choices"] if c["is_correct"])
            post_data[f"q_{sq['question_id']}"] = [str(correct_choice_id)]
        resp = client.post(attempt_url, post_data)
        assert resp.status_code == 302

        results_url = reverse(
            "licensing:diagnostic_results",
            kwargs={"test_slug": diagnostic_test.slug, "attempt_uuid": attempt.uuid},
        )
        resp = client.get(results_url)
        assert resp.status_code == 200
        assert b"100" in resp.content  # score_percent rendered

        attempt.refresh_from_db()
        assert attempt.score_percent == 100
        assert attempt.report_pdf.name  # generated on submit

    def test_intro_requires_a_name(self, diagnostic_test):
        client = Client()
        intro_url = reverse("licensing:diagnostic_intro", kwargs={"test_slug": diagnostic_test.slug})
        resp = client.post(intro_url, {"student_name": ""})
        assert resp.status_code == 200  # re-renders with an error, doesn't create an attempt
        assert DiagnosticAttempt.objects.count() == 0

    def test_inactive_diagnostic_404s(self, diagnostic_test):
        diagnostic_test.is_active = False
        diagnostic_test.save(update_fields=["is_active"])
        client = Client()
        resp = client.get(reverse("licensing:diagnostic_intro", kwargs={"test_slug": diagnostic_test.slug}))
        assert resp.status_code == 404
