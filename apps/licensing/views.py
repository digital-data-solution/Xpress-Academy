import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .diagnostics import (
    expire_diagnostic_attempt_if_stale,
    finalize_diagnostic_attempt,
    generate_and_save_report_pdf,
    save_diagnostic_answer,
    serialize_snapshot_for_display,
    start_diagnostic_attempt,
)
from .models import DiagnosticAttempt, DiagnosticMockTest


def _get_test(test_slug):
    return get_object_or_404(DiagnosticMockTest, slug=test_slug, is_active=True)


def _get_attempt(test, attempt_uuid):
    # Public, unauthenticated flow — the UUID itself is the only
    # access control (see DiagnosticAttempt's own docstring). A bad or
    # foreign uuid 404s cleanly, never a leaked 500.
    return get_object_or_404(DiagnosticAttempt, uuid=attempt_uuid, test=test)


def diagnostic_intro(request, test_slug):
    test = _get_test(test_slug)

    if request.method == "POST":
        student_name = (request.POST.get("student_name") or "").strip()
        student_email = (request.POST.get("student_email") or "").strip()
        school_name = (request.POST.get("school_name") or "").strip()
        if not student_name:
            return render(request, "licensing/diagnostic_intro.html", {
                "test": test, "error": "Please enter your name to start.",
            })
        attempt = start_diagnostic_attempt(
            test, student_name=student_name, student_email=student_email, school_name=school_name,
        )
        return redirect("licensing:diagnostic_attempt", test_slug=test.slug, attempt_uuid=attempt.uuid)

    return render(request, "licensing/diagnostic_intro.html", {"test": test})


def diagnostic_attempt_view(request, test_slug, attempt_uuid):
    test = _get_test(test_slug)
    attempt = _get_attempt(test, attempt_uuid)
    attempt = expire_diagnostic_attempt_if_stale(attempt)

    if not attempt.is_in_progress:
        return redirect("licensing:diagnostic_results", test_slug=test.slug, attempt_uuid=attempt.uuid)

    if request.method == "POST":
        for sq in attempt.question_snapshot:
            raw_ids = request.POST.getlist(f"q_{sq['question_id']}")
            if raw_ids:
                save_diagnostic_answer(attempt, sq["question_id"], [int(c) for c in raw_ids])
        finalize_diagnostic_attempt(attempt)
        generate_and_save_report_pdf(attempt)
        return redirect("licensing:diagnostic_results", test_slug=test.slug, attempt_uuid=attempt.uuid)

    existing_answers = {a.question_id: a.selected_choice_ids for a in attempt.answers.all()}
    questions = serialize_snapshot_for_display(attempt)
    for q in questions:
        q["selected"] = existing_answers.get(q["question_id"], [])

    return render(request, "licensing/diagnostic_attempt.html", {
        "test": test, "attempt": attempt, "questions": questions,
    })


@require_POST
def diagnostic_save_answer_ajax(request, test_slug, attempt_uuid):
    test = _get_test(test_slug)
    attempt = _get_attempt(test, attempt_uuid)
    attempt = expire_diagnostic_attempt_if_stale(attempt)
    if not attempt.is_in_progress:
        return JsonResponse({"ok": False, "error": "Attempt already submitted."}, status=409)

    try:
        payload = json.loads(request.body)
        question_id = int(payload["question_id"])
        choice_ids = [int(c) for c in payload.get("choice_ids", [])]
    except (KeyError, ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "error": "Malformed request."}, status=400)

    try:
        save_diagnostic_answer(attempt, question_id, choice_ids)
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    return JsonResponse({"ok": True})


def diagnostic_results_view(request, test_slug, attempt_uuid):
    test = _get_test(test_slug)
    attempt = _get_attempt(test, attempt_uuid)
    if attempt.is_in_progress:
        return redirect("licensing:diagnostic_attempt", test_slug=test.slug, attempt_uuid=attempt.uuid)

    answers_by_question = {a.question_id: a for a in attempt.answers.all()}
    rows = []
    for sq in attempt.question_snapshot:
        answer = answers_by_question.get(sq["question_id"])
        selected_ids = set(answer.selected_choice_ids) if answer else set()
        rows.append({
            "stem": sq["stem"],
            "explanation": sq["explanation"],
            "topic": sq.get("topic"),
            "choices": [
                {"text": c["text"], "is_correct": c["is_correct"], "was_selected": c["choice_id"] in selected_ids}
                for c in sq["choices"]
            ],
            "answered_correctly": answer.is_correct if answer else False,
            "answered": answer is not None,
        })

    return render(request, "licensing/diagnostic_results.html", {
        "test": test, "attempt": attempt, "rows": rows,
    })
