import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import requires_quiz_access
from .models import Attempt
from .services import (
    can_start_new_attempt,
    expire_attempt_if_stale,
    finalize_attempt,
    get_active_attempt,
    save_answer,
    serialize_snapshot_for_display,
    start_attempt,
)


def _get_owned_attempt(request, attempt_id):
    return get_object_or_404(Attempt, pk=attempt_id, enrollment=request.enrollment, quiz=request.quiz)


@requires_quiz_access
def quiz_intro(request, course_slug, quiz_id):
    quiz = request.quiz
    enrollment = request.enrollment

    active = get_active_attempt(enrollment, quiz)
    if active:
        return redirect("assessment:attempt", course_slug=course_slug, quiz_id=quiz_id, attempt_id=active.id)

    if request.method == "POST":
        try:
            attempt = start_attempt(enrollment, quiz)
        except ValueError:
            pass  # attempt limit reached — fall through to render intro with the message below
        else:
            return redirect("assessment:attempt", course_slug=course_slug, quiz_id=quiz_id, attempt_id=attempt.id)

    past_attempts = Attempt.objects.filter(
        enrollment=enrollment, quiz=quiz, submitted_at__isnull=False
    ).order_by("-started_at")

    return render(request, "assessment/quiz_intro.html", {
        "course": request.course,
        "quiz": quiz,
        "past_attempts": past_attempts,
        "can_start": can_start_new_attempt(enrollment, quiz),
    })


@requires_quiz_access
def attempt_view(request, course_slug, quiz_id, attempt_id):
    attempt = _get_owned_attempt(request, attempt_id)
    attempt = expire_attempt_if_stale(attempt)

    if not attempt.is_in_progress:
        return redirect("assessment:results", course_slug=course_slug, quiz_id=quiz_id, attempt_id=attempt.id)

    if request.method == "POST":
        # Re-save from the submitted form state before finalizing —
        # this is what makes the final "Submit quiz" button correct
        # on its own even if per-question autosave never ran (JS
        # disabled, or every autosave request failed on a bad
        # connection). getlist() works uniformly for a radio group
        # (MCQ/TRUE_FALSE) or a checkbox group (MULTI_SELECT); a
        # question with nothing submitted is left as whatever
        # autosave already has for it (or unanswered).
        for sq in attempt.question_snapshot:
            raw_ids = request.POST.getlist(f"q_{sq['question_id']}")
            if raw_ids:
                save_answer(attempt, sq["question_id"], [int(c) for c in raw_ids])
        finalize_attempt(attempt)
        return redirect("assessment:results", course_slug=course_slug, quiz_id=quiz_id, attempt_id=attempt.id)

    existing_answers = {
        a.question_id: list(a.selected_choices.values_list("id", flat=True))
        for a in attempt.answers.all()
    }
    questions = serialize_snapshot_for_display(attempt)
    for q in questions:
        q["selected"] = existing_answers.get(q["question_id"], [])

    return render(request, "assessment/attempt.html", {
        "course": request.course,
        "quiz": request.quiz,
        "attempt": attempt,
        "questions": questions,
    })


@require_POST
@requires_quiz_access
def save_answer_ajax(request, course_slug, quiz_id, attempt_id):
    attempt = _get_owned_attempt(request, attempt_id)
    attempt = expire_attempt_if_stale(attempt)
    if not attempt.is_in_progress:
        return JsonResponse({"ok": False, "error": "Attempt already submitted."}, status=409)

    try:
        payload = json.loads(request.body)
        question_id = int(payload["question_id"])
        choice_ids = [int(c) for c in payload.get("choice_ids", [])]
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Malformed request."}, status=400)

    try:
        save_answer(attempt, question_id, choice_ids)
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    return JsonResponse({"ok": True})


@requires_quiz_access
def results_view(request, course_slug, quiz_id, attempt_id):
    attempt = _get_owned_attempt(request, attempt_id)
    if attempt.is_in_progress:
        return redirect("assessment:attempt", course_slug=course_slug, quiz_id=quiz_id, attempt_id=attempt.id)

    answers_by_question = {a.question_id: a for a in attempt.answers.all()}
    rows = []
    for sq in attempt.question_snapshot:
        answer = answers_by_question.get(sq["question_id"])
        selected_ids = set(answer.selected_choices.values_list("id", flat=True)) if answer else set()
        rows.append({
            "stem": sq["stem"],
            "explanation": sq["explanation"],
            "choices": [
                {
                    "text": c["text"],
                    "is_correct": c["is_correct"],
                    "was_selected": c["choice_id"] in selected_ids,
                }
                for c in sq["choices"]
            ],
            "answered_correctly": answer.is_correct if answer else False,
            "answered": answer is not None,
        })

    from apps.enrollment.services import get_next_lesson

    next_lesson = None
    certificate = None
    if attempt.enrollment:
        next_lesson = get_next_lesson(attempt.enrollment)
        certificate = getattr(attempt.enrollment, "certificate", None)

    return render(request, "assessment/results.html", {
        "course": request.course,
        "quiz": request.quiz,
        "attempt": attempt,
        "rows": rows,
        "next_lesson": next_lesson,
        "certificate": certificate,
    })
