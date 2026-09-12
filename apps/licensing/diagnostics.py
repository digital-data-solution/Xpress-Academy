"""Diagnostic mock test delivery — build spec §B's free, shareable
"door-opener for outbound." Mirrors apps.assessment.services closely
(same snapshot-at-start / grade-from-snapshot / never re-query-the-
bank-later discipline, same per-question autosave-survives-a-dropped-
connection principle) but built against DiagnosticAttempt instead of
assessment.Attempt, since a diagnostic test-taker has no Enrollment —
see licensing.models.DiagnosticMockTest's docstring for why this
isn't just a thin wrapper around the existing Quiz engine.
"""

import random

from django.db import transaction
from django.utils import timezone

from apps.assessment.services import stratified_sample_by_syllabus_topic

from .models import DiagnosticAnswer, DiagnosticAttempt, DiagnosticMockTest


def _build_diagnostic_snapshot(test: DiagnosticMockTest) -> list[dict]:
    pool = test.bank.questions.filter(is_active=True).prefetch_related("choices", "syllabus_topics")
    if test.syllabus_topic_filter.exists():
        pool = pool.filter(syllabus_topics__in=test.syllabus_topic_filter.all()).distinct()

    candidates = [q for q in pool if q.is_publishable]
    # Same real-syllabus-weighting reasoning as the real quiz engine —
    # see stratified_sample_by_syllabus_topic's own docstring. A
    # diagnostic is the very first thing a prospect sees; it should
    # look like a real JAMB paper's balance, not a lucky/unlucky draw.
    selected = stratified_sample_by_syllabus_topic(candidates, test.question_count)

    snapshot = []
    for q in selected:
        choices = list(q.choices.all())
        random.shuffle(choices)
        topic_names = [t.name for t in q.syllabus_topics.all()]
        snapshot.append({
            "question_id": q.id,
            "stem": q.stem,
            "explanation": q.explanation,
            # First syllabus topic only — a question can carry more
            # than one, but the breakdown needs one bucket per question
            # to stay simple and readable in a sales artefact, not a
            # perfectly exhaustive cross-tab.
            "topic": topic_names[0] if topic_names else "General",
            "choices": [
                {"choice_id": c.id, "text": c.text, "is_correct": c.is_correct}
                for c in choices
            ],
        })
    return snapshot


def start_diagnostic_attempt(
    test: DiagnosticMockTest, *, student_name: str, student_email: str = "", school_name: str = ""
) -> DiagnosticAttempt:
    if not test.is_active:
        raise ValueError("This diagnostic is no longer active.")

    expires_at = None
    if test.time_limit_minutes:
        expires_at = timezone.now() + timezone.timedelta(minutes=test.time_limit_minutes)

    return DiagnosticAttempt.objects.create(
        test=test,
        student_name=student_name,
        student_email=student_email,
        school_name=school_name,
        expires_at=expires_at,
        question_snapshot=_build_diagnostic_snapshot(test),
    )


def serialize_snapshot_for_display(attempt: DiagnosticAttempt) -> list[dict]:
    """Question/choice text only — is_correct stripped. Same rule as
    assessment.services.serialize_snapshot_for_display: this is the
    only function allowed to hand the snapshot to a template."""
    out = []
    for q in attempt.question_snapshot:
        out.append({
            "question_id": q["question_id"],
            "stem": q["stem"],
            "choices": [{"choice_id": c["choice_id"], "text": c["text"]} for c in q["choices"]],
        })
    return out


def _get_snapshot_question(attempt: DiagnosticAttempt, question_id: int) -> dict | None:
    for q in attempt.question_snapshot:
        if q["question_id"] == question_id:
            return q
    return None


@transaction.atomic
def save_diagnostic_answer(attempt: DiagnosticAttempt, question_id: int, selected_choice_ids: list[int]) -> DiagnosticAnswer:
    if not attempt.is_in_progress:
        raise ValueError("This attempt is already submitted.")

    snapshot_question = _get_snapshot_question(attempt, question_id)
    if snapshot_question is None:
        raise ValueError("That question is not part of this attempt.")

    selected_set = set(selected_choice_ids)
    correct_ids = {c["choice_id"] for c in snapshot_question["choices"] if c["is_correct"]}
    is_correct = selected_set == correct_ids

    answer, _created = DiagnosticAnswer.objects.update_or_create(
        attempt=attempt, question_id=question_id,
        defaults={"selected_choice_ids": list(selected_set), "is_correct": is_correct},
    )
    return answer


@transaction.atomic
def finalize_diagnostic_attempt(attempt: DiagnosticAttempt) -> DiagnosticAttempt:
    if not attempt.is_in_progress:
        return attempt

    answers_by_question = {a.question_id: a for a in attempt.answers.all()}

    topic_stats: dict[str, dict[str, int]] = {}
    correct_count = 0
    for sq in attempt.question_snapshot:
        topic = sq.get("topic") or "General"
        stats = topic_stats.setdefault(topic, {"correct": 0, "total": 0})
        stats["total"] += 1
        answer = answers_by_question.get(sq["question_id"])
        if answer and answer.is_correct:
            stats["correct"] += 1
            correct_count += 1

    question_count = len(attempt.question_snapshot) or 1
    attempt.score_percent = round(correct_count * 100 / question_count)
    attempt.topic_breakdown = topic_stats
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["score_percent", "topic_breakdown", "submitted_at"])
    return attempt


def expire_diagnostic_attempt_if_stale(attempt: DiagnosticAttempt) -> DiagnosticAttempt:
    if attempt.is_expired:
        return finalize_diagnostic_attempt(attempt)
    return attempt


def generate_and_save_report_pdf(attempt: DiagnosticAttempt) -> DiagnosticAttempt:
    """Renders and persists the per-student PDF — same
    build-bytes-then-.save()-via-ContentFile pattern as
    apps.certificates.services.issue_certificate. Safe to call more
    than once (e.g. a regenerate-PDF admin action): FileField.save
    overwrites in place."""
    from django.core.files.base import ContentFile

    from .pdf import build_diagnostic_report_pdf

    pdf_bytes = build_diagnostic_report_pdf(attempt)
    attempt.report_pdf.save(f"diagnostic-{attempt.uuid}.pdf", ContentFile(pdf_bytes), save=True)
    return attempt
