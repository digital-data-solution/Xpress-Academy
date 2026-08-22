"""Coverage required by build spec §11 before Hard Stop 1:
"Quiz grading — MCQ, multi-select, partial credit rules, attempt
limits, timer expiry."
"""

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment, LessonProgress
from apps.enrollment.services import is_module_unlocked, mark_lesson_complete
from apps.organizations.models import Organization

from .csv_import import import_questions_from_csv
from .models import Attempt, AttemptAnswer, Choice, Question, QuestionBank, Quiz, Topic
from .services import (
    can_start_new_attempt,
    expire_attempt_if_stale,
    finalize_attempt,
    save_answer,
    start_attempt,
)


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience="BREEDER")
    return Course.objects.create(organization=org, programme=programme, title="Test Course", audience="BREEDER")


@pytest.fixture
def user():
    return User.objects.create_user(email="learner@example.com", password="testpass123")


@pytest.fixture
def enrollment(course, user):
    return Enrollment.objects.create(user=user, course=course)


@pytest.fixture
def bank(org):
    return QuestionBank.objects.create(organization=org, name="Test Bank")


def make_mcq(bank, correct_text="Correct"):
    q = Question.objects.create(bank=bank, type=Question.Type.MCQ, stem="An MCQ", explanation="Because.")
    Choice.objects.create(question=q, text=correct_text, is_correct=True, order=1)
    Choice.objects.create(question=q, text="Wrong 1", is_correct=False, order=2)
    Choice.objects.create(question=q, text="Wrong 2", is_correct=False, order=3)
    return q


def make_multi(bank):
    """3 correct out of 5 total choices."""
    q = Question.objects.create(bank=bank, type=Question.Type.MULTI_SELECT, stem="Pick all that apply")
    correct = [Choice.objects.create(question=q, text=f"Right {i}", is_correct=True, order=i) for i in range(3)]
    wrong = [Choice.objects.create(question=q, text=f"Wrong {i}", is_correct=False, order=i + 3) for i in range(2)]
    return q, correct, wrong


@pytest.mark.django_db
class TestGrading:
    def test_mcq_correct_scores_full(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)
        correct_choice_id = attempt.question_snapshot[0]["choices"][
            [c["is_correct"] for c in attempt.question_snapshot[0]["choices"]].index(True)
        ]["choice_id"]

        save_answer(attempt, attempt.question_snapshot[0]["question_id"], [correct_choice_id])
        finalize_attempt(attempt)
        attempt.refresh_from_db()
        assert attempt.score_percent == 100
        assert attempt.passed is True
        assert AttemptAnswer.objects.get(attempt=attempt).is_correct is True

    def test_mcq_incorrect_scores_zero(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)
        wrong_choice_id = next(
            c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if not c["is_correct"]
        )
        save_answer(attempt, attempt.question_snapshot[0]["question_id"], [wrong_choice_id])
        finalize_attempt(attempt)
        attempt.refresh_from_db()
        assert attempt.score_percent == 0
        assert attempt.passed is False

    def test_multi_select_partial_credit(self, bank, enrollment):
        q, correct, wrong = make_multi(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)

        # Select 2 of 3 correct, 0 wrong -> fraction = (2-0)/3 = 0.667 -> 67%
        save_answer(attempt, q.id, [correct[0].id, correct[1].id])
        finalize_attempt(attempt)
        attempt.refresh_from_db()
        assert attempt.score_percent == 67
        answer = AttemptAnswer.objects.get(attempt=attempt, question=q)
        assert answer.is_correct is False  # not the exact correct set

    def test_multi_select_exact_match_is_full_credit_and_marked_correct(self, bank, enrollment):
        q, correct, wrong = make_multi(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)
        save_answer(attempt, q.id, [c.id for c in correct])
        finalize_attempt(attempt)
        attempt.refresh_from_db()
        assert attempt.score_percent == 100
        assert AttemptAnswer.objects.get(attempt=attempt, question=q).is_correct is True

    def test_multi_select_wrong_selections_reduce_score_floored_at_zero(self, bank, enrollment):
        q, correct, wrong = make_multi(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)
        # 1 correct selected, 2 wrong selected -> (1-2)/3 = negative -> floored to 0
        save_answer(attempt, q.id, [correct[0].id, wrong[0].id, wrong[1].id])
        finalize_attempt(attempt)
        attempt.refresh_from_db()
        assert attempt.score_percent == 0

    def test_unanswered_question_counts_as_incorrect_not_a_blocker(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)
        finalize_attempt(attempt)  # never answered
        attempt.refresh_from_db()
        assert attempt.score_percent == 0
        assert attempt.submitted_at is not None

    def test_grading_uses_snapshot_not_live_question_data(self, bank, enrollment):
        """Editing the live Question/Choice after an attempt starts
        must not affect that attempt's grading — build spec §4."""
        q = make_mcq(bank, correct_text="Original correct")
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank, question_count=1,
        )
        attempt = start_attempt(enrollment, quiz)
        correct_choice_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if c["is_correct"])

        # Now flip which choice is correct in the live DB.
        Choice.objects.filter(question=q, is_correct=True).update(is_correct=False)
        Choice.objects.filter(question=q, id=correct_choice_id).update(is_correct=False)
        Choice.objects.filter(question=q).exclude(id=correct_choice_id).update(is_correct=True)

        # Grade against the ORIGINAL snapshot answer — should still be correct.
        save_answer(attempt, attempt.question_snapshot[0]["question_id"], [correct_choice_id])
        finalize_attempt(attempt)
        attempt.refresh_from_db()
        assert attempt.score_percent == 100, "must grade from the snapshot, not the now-changed live Choice rows"


@pytest.mark.django_db
class TestAttemptLimitsAndTimer:
    def test_unlimited_attempts_by_default(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank,
            question_count=1, max_attempts=0,
        )
        for _ in range(5):
            attempt = start_attempt(enrollment, quiz)
            finalize_attempt(attempt)
        assert can_start_new_attempt(enrollment, quiz) is True

    def test_attempt_limit_enforced(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank,
            question_count=1, max_attempts=2,
        )
        for _ in range(2):
            attempt = start_attempt(enrollment, quiz)
            finalize_attempt(attempt)
        assert can_start_new_attempt(enrollment, quiz) is False
        with pytest.raises(ValueError):
            start_attempt(enrollment, quiz)

    def test_resuming_an_in_progress_attempt_does_not_consume_a_slot(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank,
            question_count=1, max_attempts=1,
        )
        a1 = start_attempt(enrollment, quiz)  # in progress, not submitted
        a2 = start_attempt(enrollment, quiz)  # should return the same attempt, not error
        assert a1.id == a2.id

    def test_expired_attempt_auto_finalizes_with_answers_given(self, bank, enrollment):
        q = make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank,
            question_count=1, time_limit_minutes=10,
        )
        attempt = start_attempt(enrollment, quiz)
        correct_choice_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if c["is_correct"])
        save_answer(attempt, q.id, [correct_choice_id])  # answered before expiry

        attempt.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        attempt.save(update_fields=["expires_at"])

        result = expire_attempt_if_stale(attempt)
        assert result.submitted_at is not None
        assert result.score_percent == 100, "the answer given before expiry must still be graded"

    def test_no_time_limit_never_expires(self, bank, enrollment):
        make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=enrollment.course, title="Final", bank=bank,
            question_count=1, time_limit_minutes=0,
        )
        attempt = start_attempt(enrollment, quiz)
        assert attempt.is_expired is False


@pytest.mark.django_db
class TestCSVImport:
    def test_valid_csv_creates_questions(self, bank):
        csv_content = (
            "stem,type,difficulty,explanation,topics,choice_1,choice_1_correct,choice_2,choice_2_correct\n"
            "What is 2+2?,MCQ,EASY,Basic maths.,Arithmetic,4,TRUE,5,FALSE\n"
        )
        import io
        result = import_questions_from_csv(bank, io.BytesIO(csv_content.encode()))
        assert result.created == 1
        assert not result.errors
        q = Question.objects.get(bank=bank)
        assert q.choices.count() == 2
        assert Topic.objects.filter(name="Arithmetic").exists()

    def test_row_with_wrong_correct_count_for_mcq_is_skipped(self, bank):
        csv_content = (
            "stem,type,choice_1,choice_1_correct,choice_2,choice_2_correct\n"
            "Bad row,MCQ,A,TRUE,B,TRUE\n"  # two correct on an MCQ — invalid
        )
        import io
        result = import_questions_from_csv(bank, io.BytesIO(csv_content.encode()))
        assert result.created == 0
        assert len(result.errors) == 1
        assert Question.objects.filter(bank=bank).count() == 0

    def test_missing_required_column(self, bank):
        import io
        result = import_questions_from_csv(bank, io.BytesIO(b"foo,bar\n1,2\n"))
        assert result.created == 0
        assert "Missing required column" in result.errors[0]


def make_module(course, order, unlock_rule=Module.UnlockRule.SEQUENTIAL, requires_quiz=False):
    module = Module.objects.create(
        course=course, order=order, title=f"Module {order}",
        unlock_rule=unlock_rule, requires_quiz_pass_to_advance=requires_quiz,
    )
    Lesson.objects.create(module=module, order=1, title=f"Lesson {order}.1", type=Lesson.Type.TEXT)
    return module


@pytest.mark.django_db
class TestQuizGatesProgress:
    def test_module_quiz_pass_required_to_unlock_next_module(self, bank, course, enrollment):
        m1 = make_module(course, 1, requires_quiz=True)
        m2 = make_module(course, 2)
        q = make_mcq(bank)
        quiz = Quiz.objects.create(scope=Quiz.Scope.MODULE, module=m1, title="M1 Quiz", bank=bank, question_count=1)

        mark_lesson_complete(enrollment, m1.lessons.first())
        assert is_module_unlocked(enrollment, m2) is False, "lessons done but quiz not passed — still locked"

        attempt = start_attempt(enrollment, quiz)
        correct_choice_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if c["is_correct"])
        save_answer(attempt, q.id, [correct_choice_id])
        finalize_attempt(attempt)

        assert is_module_unlocked(enrollment, m2) is True

    def test_failing_module_quiz_keeps_next_module_locked(self, bank, course, enrollment):
        m1 = make_module(course, 1, requires_quiz=True)
        m2 = make_module(course, 2)
        q = make_mcq(bank)
        quiz = Quiz.objects.create(
            scope=Quiz.Scope.MODULE, module=m1, title="M1 Quiz", bank=bank, question_count=1, pass_mark=100,
        )
        mark_lesson_complete(enrollment, m1.lessons.first())

        attempt = start_attempt(enrollment, quiz)
        wrong_choice_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if not c["is_correct"])
        save_answer(attempt, q.id, [wrong_choice_id])
        finalize_attempt(attempt)

        assert is_module_unlocked(enrollment, m2) is False

    def test_final_quiz_pass_required_for_course_completion(self, bank, course, enrollment):
        course.requires_final_assessment = True
        course.save(update_fields=["requires_final_assessment"])
        m1 = make_module(course, 1)
        q = make_mcq(bank)
        final_quiz = Quiz.objects.create(scope=Quiz.Scope.FINAL, course=course, title="Final", bank=bank, question_count=1)

        mark_lesson_complete(enrollment, m1.lessons.first())
        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.ACTIVE, "all lessons done but final not passed yet"

        attempt = start_attempt(enrollment, final_quiz)
        correct_choice_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if c["is_correct"])
        save_answer(attempt, q.id, [correct_choice_id])
        finalize_attempt(attempt)

        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.COMPLETED
        assert enrollment.completed_at is not None


@pytest.mark.django_db
class TestQuizHTTPFlow:
    def test_full_flow_start_answer_submit_results(self, bank, course, enrollment, user):
        m1 = make_module(course, 1)
        q = make_mcq(bank)
        quiz = Quiz.objects.create(scope=Quiz.Scope.MODULE, module=m1, title="M1 Quiz", bank=bank, question_count=1)

        client = Client(raise_request_exception=True)
        client.force_login(user)

        # Intro page
        resp = client.get(f"/learn/{course.slug}/quiz/{quiz.id}/")
        assert resp.status_code == 200

        # Start
        resp = client.post(f"/learn/{course.slug}/quiz/{quiz.id}/")
        assert resp.status_code == 302
        attempt = Attempt.objects.get(enrollment=enrollment, quiz=quiz)
        attempt_url = f"/learn/{course.slug}/quiz/{quiz.id}/attempt/{attempt.id}/"
        assert resp["Location"] == attempt_url

        # Attempt page renders without leaking is_correct into the HTML
        resp = client.get(attempt_url)
        assert resp.status_code == 200
        assert b"is_correct" not in resp.content

        # Autosave one answer via the JSON endpoint
        correct_choice_id = next(c["choice_id"] for c in attempt.question_snapshot[0]["choices"] if c["is_correct"])
        resp = client.post(
            attempt_url + "answer/",
            data={"question_id": q.id, "choice_ids": [correct_choice_id]},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

        # Submit (plain form POST, no fields — relies on already-autosaved answer)
        resp = client.post(attempt_url)
        assert resp.status_code == 302
        results_url = f"/learn/{course.slug}/quiz/{quiz.id}/attempt/{attempt.id}/results/"
        assert resp["Location"] == results_url

        resp = client.get(results_url)
        assert resp.status_code == 200
        assert b"100" in resp.content

    def test_locked_module_quiz_not_accessible(self, bank, course, enrollment, user):
        m1 = make_module(course, 1)
        m2 = make_module(course, 2)
        make_mcq(bank)
        quiz = Quiz.objects.create(scope=Quiz.Scope.MODULE, module=m2, title="M2 Quiz", bank=bank, question_count=1)

        client = Client(raise_request_exception=True)
        client.force_login(user)
        resp = client.get(f"/learn/{course.slug}/quiz/{quiz.id}/")
        assert resp.status_code == 302  # redirected to curriculum, module 2 locked

    def test_unenrolled_user_gets_403(self, bank, course, user):
        m1 = make_module(course, 1)
        make_mcq(bank)
        quiz = Quiz.objects.create(scope=Quiz.Scope.MODULE, module=m1, title="M1 Quiz", bank=bank, question_count=1)
        client = Client(raise_request_exception=True)
        client.force_login(user)
        resp = client.get(f"/learn/{course.slug}/quiz/{quiz.id}/")
        assert resp.status_code == 403
