"""Scoring, CSV export, and pre/post pairing — kept out of views.py so
the pairing logic (the one genuinely differentiated feature here) has
a single, testable home."""
import csv
import io
from django.utils import timezone

from .models import Choice, Question, Quiz, Response, TrainingSession


def create_quiz_with_questions(*, user, quiz_form, question_forms) -> Quiz:
    """quiz_form and question_forms must already be validated (is_valid()
    called and True) by the caller — this only does the DB writes."""
    quiz = quiz_form.save(commit=False)
    quiz.created_by = user
    quiz.save()
    _save_questions(quiz, question_forms)
    return quiz


def replace_quiz_questions(*, quiz: Quiz, question_forms) -> None:
    """Used by quiz_edit — simplest-correct approach for a quiz with no
    responses yet: drop and recreate every question. NOT called once a
    quiz has responses (the view blocks editing questions at that
    point, since existing Response.answers reference these Question/
    Choice ids directly — see the model's "No snapshotting" note)."""
    quiz.questions.all().delete()
    _save_questions(quiz, question_forms)


def _save_questions(quiz: Quiz, question_forms) -> None:
    order = 0
    for qf in question_forms:
        if qf.cleaned_data.get("DELETE"):
            continue
        stem = qf.cleaned_data.get("stem")
        if not stem:
            continue
        question = Question.objects.create(quiz=quiz, order=order, stem=stem)
        order += 1
        correct_letter = qf.cleaned_data["correct_option"]
        choice_order = 0
        for letter, field_name in qf.options():
            text = qf.cleaned_data.get(field_name)
            if not text:
                continue
            Choice.objects.create(
                question=question, order=choice_order, text=text, is_correct=(letter == correct_letter)
            )
            choice_order += 1


def score_and_submit_response(*, response: Response, posted_answers: dict) -> Response:
    """posted_answers: {"<question_id>": "<choice_id>", ...} straight
    from request.POST. Grades against the live Question/Choice rows —
    safe per the model's "No snapshotting" note."""
    questions = list(response.quiz.questions.prefetch_related("choices"))
    total = len(questions)
    correct = 0
    clean_answers = {}
    for q in questions:
        chosen_id = posted_answers.get(str(q.id))
        if not chosen_id:
            continue
        clean_answers[str(q.id)] = chosen_id
        chosen = next((c for c in q.choices.all() if str(c.id) == str(chosen_id)), None)
        if chosen and chosen.is_correct:
            correct += 1

    response.answers = clean_answers
    response.score_percent = round((correct / total) * 100) if total else 0
    response.submitted_at = timezone.now()
    response.save()
    return response


def response_rows_for_export(quiz: Quiz):
    """Yields one dict per submitted response, columns fixed
    (name/email/score/submitted_at) plus one column per question —
    the shape both quiz_export_csv and the template's preview table use."""
    questions = list(quiz.questions.prefetch_related("choices"))
    responses = quiz.responses.filter(submitted_at__isnull=False).order_by("submitted_at")
    for r in responses:
        row = {
            "name": r.respondent_name,
            "email": r.respondent_email,
            "score_percent": r.score_percent,
            "submitted_at": r.submitted_at,
        }
        for q in questions:
            chosen_id = r.answers.get(str(q.id))
            chosen = next((c for c in q.choices.all() if str(c.id) == str(chosen_id)), None)
            row[f"Q{q.order + 1}"] = chosen.text if chosen else ""
        yield row


def write_csv(rows, fieldnames) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def quiz_export_csv_content(quiz: Quiz) -> str:
    questions = list(quiz.questions.all())
    fieldnames = ["name", "email", "score_percent", "submitted_at"] + [f"Q{q.order + 1}" for q in questions]
    return write_csv(response_rows_for_export(quiz), fieldnames)


def question_to_formset_initial(question: Question) -> dict:
    """Builds one QuestionFormSet initial-data dict from an existing
    Question+Choice set — used by quiz_edit to prefill the form. A
    question with fewer than 4 choices (e.g. a true/false-style
    2-option one) just leaves option_c/option_d blank."""
    choices_by_order = {c.order: c for c in question.choices.all()}
    letters = ["a", "b", "c", "d"]
    data = {"stem": question.stem}
    correct_letter = "a"
    for i, letter in enumerate(letters):
        choice = choices_by_order.get(i)
        data[f"option_{letter}"] = choice.text if choice else ""
        if choice and choice.is_correct:
            correct_letter = letter
    data["correct_option"] = correct_letter
    return data


def paired_session_rows(session: TrainingSession):
    """Joins pre_quiz and post_quiz responses by respondent_email
    (case-insensitively) — the actual pre/post delta report, and the
    concrete feature this whole app was built to offer that Google/
    Microsoft Forms don't. A person who only took one side still gets
    a row, with the other side blank — partial attendance shouldn't
    silently vanish from a training record."""
    pre_by_email, post_by_email = {}, {}
    if session.pre_quiz_id:
        for r in session.pre_quiz.responses.filter(submitted_at__isnull=False):
            pre_by_email[r.respondent_email.lower()] = r
    if session.post_quiz_id:
        for r in session.post_quiz.responses.filter(submitted_at__isnull=False):
            post_by_email[r.respondent_email.lower()] = r

    all_emails = sorted(set(pre_by_email) | set(post_by_email))
    rows = []
    for email in all_emails:
        pre = pre_by_email.get(email)
        post = post_by_email.get(email)
        pre_score = pre.score_percent if pre else None
        post_score = post.score_percent if post else None
        delta = (post_score - pre_score) if (pre_score is not None and post_score is not None) else None
        rows.append({
            "name": (post or pre).respondent_name,
            "email": email,
            "pre_score": pre_score,
            "post_score": post_score,
            "delta": delta,
        })
    return rows


def session_export_csv_content(session: TrainingSession) -> str:
    fieldnames = ["name", "email", "pre_score", "post_score", "delta"]
    return write_csv(paired_session_rows(session), fieldnames)
