from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Choice, Question, Quiz, Response, TrainingSession

User = get_user_model()


def make_quiz_with_one_question(owner, correct_text="Paris", quiz_kwargs=None):
    kwargs = {"title": "Capitals", **(quiz_kwargs or {})}
    quiz = Quiz.objects.create(created_by=owner, **kwargs)
    q = Question.objects.create(quiz=quiz, order=0, stem="Capital of France?")
    Choice.objects.create(question=q, order=0, text=correct_text, is_correct=True)
    Choice.objects.create(question=q, order=1, text="London", is_correct=False)
    Choice.objects.create(question=q, order=2, text="Berlin", is_correct=False)
    return quiz, q


class QuizModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="trainer@example.com", password="x")

    def test_slug_auto_generated_and_unique(self):
        q1 = Quiz.objects.create(created_by=self.user, title="Safety Training")
        q2 = Quiz.objects.create(created_by=self.user, title="Safety Training")
        self.assertEqual(q1.slug, "safety-training")
        self.assertNotEqual(q1.slug, q2.slug)
        self.assertTrue(q2.slug.startswith("safety-training"))

    def test_question_count_and_response_count(self):
        quiz, _ = make_quiz_with_one_question(self.user)
        self.assertEqual(quiz.question_count, 1)
        self.assertEqual(quiz.response_count, 0)
        r = Response.objects.create(quiz=quiz, respondent_name="A", respondent_email="a@x.com")
        self.assertEqual(quiz.response_count, 0)  # not submitted yet
        r.submitted_at = r.created_at
        r.save()
        self.assertEqual(quiz.response_count, 1)


class ScoringServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="trainer2@example.com", password="x")

    def test_score_all_correct(self):
        quiz, q = make_quiz_with_one_question(self.user)
        correct_choice = q.choices.get(is_correct=True)
        response = Response.objects.create(quiz=quiz, respondent_name="Bob", respondent_email="bob@x.com")
        services.score_and_submit_response(
            response=response, posted_answers={str(q.id): str(correct_choice.id)}
        )
        self.assertEqual(response.score_percent, 100)
        self.assertIsNotNone(response.submitted_at)

    def test_score_all_wrong(self):
        quiz, q = make_quiz_with_one_question(self.user)
        wrong_choice = q.choices.get(text="London")
        response = Response.objects.create(quiz=quiz, respondent_name="Bob", respondent_email="bob@x.com")
        services.score_and_submit_response(
            response=response, posted_answers={str(q.id): str(wrong_choice.id)}
        )
        self.assertEqual(response.score_percent, 0)

    def test_unanswered_question_counts_as_wrong_not_excluded(self):
        quiz, q = make_quiz_with_one_question(self.user)
        response = Response.objects.create(quiz=quiz, respondent_name="Bob", respondent_email="bob@x.com")
        services.score_and_submit_response(response=response, posted_answers={})
        self.assertEqual(response.score_percent, 0)


class TrainingSessionPairingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="trainer3@example.com", password="x")

    def test_pairs_by_email_case_insensitive_with_delta(self):
        pre_quiz, pre_q = make_quiz_with_one_question(self.user, quiz_kwargs={"title": "Pre"})
        post_quiz, post_q = make_quiz_with_one_question(self.user, quiz_kwargs={"title": "Post"})
        session = TrainingSession.objects.create(
            created_by=self.user, title="Session 1", pre_quiz=pre_quiz, post_quiz=post_quiz
        )

        pre_wrong = pre_q.choices.get(text="London")
        pre_resp = Response.objects.create(quiz=pre_quiz, respondent_name="Ada", respondent_email="Ada@Example.com")
        services.score_and_submit_response(response=pre_resp, posted_answers={str(pre_q.id): str(pre_wrong.id)})

        post_correct = post_q.choices.get(is_correct=True)
        post_resp = Response.objects.create(quiz=post_quiz, respondent_name="Ada", respondent_email="ada@example.com")
        services.score_and_submit_response(response=post_resp, posted_answers={str(post_q.id): str(post_correct.id)})

        rows = services.paired_session_rows(session)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["pre_score"], 0)
        self.assertEqual(row["post_score"], 100)
        self.assertEqual(row["delta"], 100)

    def test_partial_attendance_still_produces_a_row(self):
        pre_quiz, pre_q = make_quiz_with_one_question(self.user, quiz_kwargs={"title": "Pre only"})
        post_quiz, _ = make_quiz_with_one_question(self.user, quiz_kwargs={"title": "Post only"})
        session = TrainingSession.objects.create(
            created_by=self.user, title="Session 2", pre_quiz=pre_quiz, post_quiz=post_quiz
        )
        correct = pre_q.choices.get(is_correct=True)
        resp = Response.objects.create(quiz=pre_quiz, respondent_name="Chidi", respondent_email="chidi@x.com")
        services.score_and_submit_response(response=resp, posted_answers={str(pre_q.id): str(correct.id)})

        rows = services.paired_session_rows(session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pre_score"], 100)
        self.assertIsNone(rows[0]["post_score"])
        self.assertIsNone(rows[0]["delta"])


class ViewAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="x")
        self.other = User.objects.create_user(email="other@example.com", password="x")
        self.quiz, self.q = make_quiz_with_one_question(self.owner)

    def test_my_quizzes_requires_login(self):
        resp = self.client.get(reverse("quizbuilder:my_quizzes"))
        self.assertEqual(resp.status_code, 302)

    def test_quiz_take_is_public(self):
        resp = self.client.get(reverse("quizbuilder:quiz_take", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 200)

    def test_inactive_quiz_take_404s(self):
        self.quiz.is_active = False
        self.quiz.save()
        resp = self.client.get(reverse("quizbuilder:quiz_take", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 404)

    def test_only_owner_can_see_responses(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("quizbuilder:quiz_responses", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_see_responses(self):
        self.client.force_login(self.owner)
        resp = self.client.get(reverse("quizbuilder:quiz_responses", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 200)

    def test_full_take_flow_creates_scored_response(self):
        correct_choice = self.q.choices.get(is_correct=True)
        resp = self.client.post(
            reverse("quizbuilder:quiz_take", kwargs={"slug": self.quiz.slug}),
            data={
                "respondent_name": "Zara",
                "respondent_email": "zara@example.com",
                f"question_{self.q.id}": str(correct_choice.id),
            },
        )
        self.assertEqual(resp.status_code, 302)
        response = Response.objects.get(quiz=self.quiz, respondent_email="zara@example.com")
        self.assertEqual(response.score_percent, 100)

    def test_quiz_export_csv_owner_only(self):
        self.client.force_login(self.other)
        resp = self.client.get(reverse("quizbuilder:quiz_export_csv", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 404)

        self.client.force_login(self.owner)
        resp = self.client.get(reverse("quizbuilder:quiz_export_csv", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")


class QuizCreateFormTests(TestCase):
    """Covers the formset wiring end-to-end — the riskiest hand-built
    part of this feature (flat option_a..option_d fields standing in
    for a real nested Question+Choice formset)."""

    def setUp(self):
        self.user = User.objects.create_user(email="creator@example.com", password="x")
        self.client.force_login(self.user)

    def _formset_payload(self, count=2, **overrides):
        data = {
            "title": "New Hire Orientation",
            "description": "",
            "time_limit_minutes": "0",
            "show_score_immediately": "on",
            "q-TOTAL_FORMS": str(count),
            "q-INITIAL_FORMS": "0",
            "q-MIN_NUM_FORMS": "1",
            "q-MAX_NUM_FORMS": "1000",
        }
        for i in range(count):
            data.update({
                f"q-{i}-stem": f"Question {i}?",
                f"q-{i}-option_a": "Right",
                f"q-{i}-option_b": "Wrong 1",
                f"q-{i}-option_c": "Wrong 2",
                f"q-{i}-option_d": "",
                f"q-{i}-correct_option": "a",
            })
        data.update(overrides)
        return data

    def test_quiz_create_get_renders(self):
        resp = self.client.get(reverse("quizbuilder:quiz_create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Add another question")

    def test_create_quiz_with_two_questions(self):
        resp = self.client.post(reverse("quizbuilder:quiz_create"), data=self._formset_payload(count=2))
        quiz = Quiz.objects.get(title="New Hire Orientation")
        self.assertRedirects(resp, reverse("quizbuilder:quiz_created", kwargs={"slug": quiz.slug}))
        self.assertEqual(quiz.created_by, self.user)
        self.assertEqual(quiz.question_count, 2)
        first_question = quiz.questions.first()
        self.assertEqual(first_question.choices.count(), 3)  # option_d left blank
        self.assertEqual(first_question.choices.get(is_correct=True).text, "Right")

    def test_correct_option_pointing_at_blank_field_is_rejected(self):
        resp = self.client.post(
            reverse("quizbuilder:quiz_create"),
            data=self._formset_payload(count=1, **{"q-0-correct_option": "d", "q-0-option_d": ""}),
        )
        self.assertEqual(resp.status_code, 200)  # re-rendered with errors, not redirected
        self.assertFalse(Quiz.objects.filter(title="New Hire Orientation").exists())

    def test_edit_locked_once_quiz_has_a_response(self):
        quiz, q = make_quiz_with_one_question(self.user)
        Response.objects.create(
            quiz=quiz, respondent_name="X", respondent_email="x@example.com",
            submitted_at=quiz.created_at,
        )
        resp = self.client.get(reverse("quizbuilder:quiz_edit", kwargs={"slug": quiz.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["editable_questions"])
        self.assertIsNone(resp.context["formset"])

    def test_edit_unlocked_with_no_responses_prefills_formset(self):
        quiz, q = make_quiz_with_one_question(self.user)
        resp = self.client.get(reverse("quizbuilder:quiz_edit", kwargs={"slug": quiz.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["editable_questions"])
        self.assertEqual(resp.context["formset"].initial[0]["stem"], "Capital of France?")
        self.assertEqual(resp.context["formset"].initial[0]["correct_option"], "a")


class TemplateSmokeTests(TestCase):
    """Every remaining template not already exercised above — Django's
    test client raises on a real template syntax/context error during
    render, so a 200 here is a genuine smoke test, not just a status check."""

    def setUp(self):
        self.user = User.objects.create_user(email="smoke@example.com", password="x")
        self.client.force_login(self.user)
        self.quiz, self.q = make_quiz_with_one_question(self.user)

    def test_quiz_created_page(self):
        resp = self.client.get(reverse("quizbuilder:quiz_created", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 200)

    def test_my_quizzes_with_a_quiz_listed(self):
        resp = self.client.get(reverse("quizbuilder:my_quizzes"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.quiz.title)

    def test_quiz_responses_with_a_row(self):
        correct = self.q.choices.get(is_correct=True)
        response = Response.objects.create(quiz=self.quiz, respondent_name="Y", respondent_email="y@example.com")
        services.score_and_submit_response(response=response, posted_answers={str(self.q.id): str(correct.id)})
        resp = self.client.get(reverse("quizbuilder:quiz_responses", kwargs={"slug": self.quiz.slug}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "y@example.com")

    def test_quiz_result_page_with_review(self):
        correct = self.q.choices.get(is_correct=True)
        response = Response.objects.create(quiz=self.quiz, respondent_name="Z", respondent_email="z@example.com")
        services.score_and_submit_response(response=response, posted_answers={str(self.q.id): str(correct.id)})
        resp = self.client.get(
            reverse("quizbuilder:quiz_result", kwargs={"slug": self.quiz.slug, "response_uuid": response.uuid})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "100")

    def test_session_list_and_form_pages(self):
        resp = self.client.get(reverse("quizbuilder:session_list"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get(reverse("quizbuilder:session_create"))
        self.assertEqual(resp.status_code, 200)

    def test_session_report_page(self):
        session = TrainingSession.objects.create(
            created_by=self.user, title="Onboarding", pre_quiz=self.quiz, post_quiz=self.quiz
        )
        resp = self.client.get(reverse("quizbuilder:session_report", kwargs={"pk": session.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_session_report_with_paired_rows_renders(self):
        correct = self.q.choices.get(is_correct=True)
        response = Response.objects.create(quiz=self.quiz, respondent_name="P", respondent_email="p@example.com")
        services.score_and_submit_response(response=response, posted_answers={str(self.q.id): str(correct.id)})
        session = TrainingSession.objects.create(
            created_by=self.user, title="Onboarding 2", pre_quiz=self.quiz, post_quiz=self.quiz
        )
        resp = self.client.get(reverse("quizbuilder:session_report", kwargs={"pk": session.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "p@example.com")

    def test_session_export_csv(self):
        session = TrainingSession.objects.create(
            created_by=self.user, title="Onboarding 3", pre_quiz=self.quiz, post_quiz=self.quiz
        )
        resp = self.client.get(reverse("quizbuilder:session_export_csv", kwargs={"pk": session.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "text/csv")
