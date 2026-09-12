import json

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
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
from .models import DiagnosticAttempt, DiagnosticMockTest, Institution, InstitutionalLicense


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


@login_required
def school_dashboard(request, institution_slug):
    """The per-school performance dashboard — build spec §B: "this is
    the renewal argument, so build it as a sales artefact, not an
    admin page." Real access control, not just UI hiding: only the
    institution's own proprietor (or platform staff, for support) can
    view it — a 404, not a 403, so a logged-in stranger can't even
    confirm another school's dashboard exists by guessing slugs (same
    reasoning as apps.assessment.access's course/quiz mismatch check)."""
    institution = get_object_or_404(Institution, slug=institution_slug)
    if institution.proprietor_id != request.user.id and not request.user.is_staff:
        raise Http404("No institution matches the given query.")

    from apps.enrollment.models import Enrollment
    from apps.enrollment.services import get_progress_percent

    licenses = institution.licenses.filter(status=InstitutionalLicense.Status.ACTIVE)
    enrollments = (
        Enrollment.objects.filter(institutional_license__in=licenses)
        .select_related("user", "course")
        .order_by("user__email", "course__title")
    )

    # One row per student, aggregated across every course their seat(s)
    # under this institution's active licence(s) actually grant —
    # scores/attempts pulled the same way assessment.Attempt already
    # records them, not re-derived.
    students: dict[int, dict] = {}
    for e in enrollments:
        row = students.setdefault(e.user_id, {"user": e.user, "courses": [], "progress_values": []})
        progress = get_progress_percent(e)
        row["courses"].append({"course": e.course, "progress": progress, "status": e.get_status_display()})
        row["progress_values"].append(progress)

    from apps.assessment.models import Attempt

    scores_by_user: dict[int, list[int]] = {}
    attempts = Attempt.objects.filter(
        enrollment__institutional_license__in=licenses, submitted_at__isnull=False
    ).values_list("enrollment__user_id", "score_percent")
    for user_id, score in attempts:
        scores_by_user.setdefault(user_id, []).append(score)

    rows = []
    for user_id, data in students.items():
        avg_progress = round(sum(data["progress_values"]) / len(data["progress_values"]))
        scores = scores_by_user.get(user_id, [])
        rows.append({
            "user": data["user"],
            "courses": data["courses"],
            "avg_progress": avg_progress,
            "avg_quiz_score": round(sum(scores) / len(scores)) if scores else None,
            "quiz_attempts": len(scores),
        })
    rows.sort(key=lambda r: -r["avg_progress"])

    total_seats = sum(lic.seats for lic in licenses)
    seats_used = sum(lic.seats_used for lic in licenses)
    cohort_avg_progress = round(sum(r["avg_progress"] for r in rows) / len(rows)) if rows else 0
    scored_rows = [r["avg_quiz_score"] for r in rows if r["avg_quiz_score"] is not None]
    cohort_avg_score = round(sum(scored_rows) / len(scored_rows)) if scored_rows else None

    return render(request, "licensing/school_dashboard.html", {
        "institution": institution,
        "licenses": licenses,
        "rows": rows,
        "total_seats": total_seats,
        "seats_used": seats_used,
        "cohort_avg_progress": cohort_avg_progress,
        "cohort_avg_score": cohort_avg_score,
    })
