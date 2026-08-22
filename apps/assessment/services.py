"""Attempt lifecycle and server-side grading.

Grading rule (spec §4 is explicit about the mechanism — snapshot at
start, grade from the snapshot, never re-query the bank — but doesn't
give a scoring formula, so this is a documented design decision):

  MCQ / TRUE_FALSE: full credit iff the selected choice set is exactly
  the one correct choice. Binary.

  MULTI_SELECT: partial credit. fraction = max(0, correct_selected -
  incorrect_selected) / total_correct_choices, capped at 1.0. Full
  credit iff the learner selected exactly the correct set (no more,
  no less) — that's also what AttemptAnswer.is_correct records, even
  though the attempt's overall score can carry partial credit from a
  near-miss.

Per-question answers save immediately (save_answer), independent of
final submission — see build spec §6's "progress must survive a
dropped connection" principle, applied here to quiz answers instead of
video watch position: a student losing 40 answers to a network drop
on a metered connection is exactly the failure this exists to prevent
(see the JAMB-pilot planning notes). finalize_attempt grades whatever
AttemptAnswer rows exist at submit/expiry time; unanswered snapshot
questions count as incorrect, not as blocking the submission.
"""

import random

from django.db import transaction
from django.utils import timezone

from .models import Attempt, AttemptAnswer, Choice, Question, Quiz


def _build_question_snapshot(quiz: Quiz) -> list[dict]:
    pool = quiz.bank.questions.filter(is_active=True).prefetch_related("choices")
    if quiz.topic_filter.exists():
        pool = pool.filter(topics__in=quiz.topic_filter.all()).distinct()

    candidates = [q for q in pool if q.is_well_formed]
    random.shuffle(candidates)
    selected = candidates[: quiz.question_count]

    snapshot = []
    for q in selected:
        choices = list(q.choices.all())
        if quiz.randomize_choices:
            random.shuffle(choices)
        snapshot.append({
            "question_id": q.id,
            "type": q.type,
            "stem": q.stem,
            "explanation": q.explanation,
            "choices": [
                {"choice_id": c.id, "text": c.text, "is_correct": c.is_correct}
                for c in choices
            ],
        })
    return snapshot


def can_start_new_attempt(enrollment, quiz: Quiz) -> bool:
    if quiz.max_attempts == 0:
        return True
    used = Attempt.objects.filter(enrollment=enrollment, quiz=quiz, submitted_at__isnull=False).count()
    return used < quiz.max_attempts


def get_active_attempt(enrollment, quiz: Quiz) -> Attempt | None:
    """An in-progress, not-yet-expired attempt to resume, if any."""
    attempt = Attempt.objects.filter(
        enrollment=enrollment, quiz=quiz, submitted_at__isnull=True
    ).order_by("-started_at").first()
    if attempt and attempt.is_expired:
        finalize_attempt(attempt)
        return None
    return attempt


def start_attempt(enrollment, quiz: Quiz) -> Attempt:
    existing = get_active_attempt(enrollment, quiz)
    if existing:
        return existing

    if not can_start_new_attempt(enrollment, quiz):
        raise ValueError("Attempt limit reached for this quiz.")

    attempt_number = Attempt.objects.filter(enrollment=enrollment, quiz=quiz).count() + 1
    expires_at = None
    if quiz.time_limit_minutes:
        expires_at = timezone.now() + timezone.timedelta(minutes=quiz.time_limit_minutes)

    return Attempt.objects.create(
        enrollment=enrollment,
        quiz=quiz,
        attempt_number=attempt_number,
        expires_at=expires_at,
        question_snapshot=_build_question_snapshot(quiz),
    )


def serialize_snapshot_for_display(attempt: Attempt) -> list[dict]:
    """Question/choice text only — is_correct stripped. This is the
    only function allowed to hand the snapshot to a template; nothing
    else should render question_snapshot directly."""
    out = []
    for q in attempt.question_snapshot:
        out.append({
            "question_id": q["question_id"],
            "type": q["type"],
            "stem": q["stem"],
            "choices": [{"choice_id": c["choice_id"], "text": c["text"]} for c in q["choices"]],
        })
    return out


def _get_snapshot_question(attempt: Attempt, question_id: int) -> dict | None:
    for q in attempt.question_snapshot:
        if q["question_id"] == question_id:
            return q
    return None


def _grade_question(snapshot_question: dict, selected_choice_ids: set[int]) -> tuple[bool, float]:
    """Returns (is_correct, fraction_earned)."""
    choices = snapshot_question["choices"]
    correct_ids = {c["choice_id"] for c in choices if c["is_correct"]}

    if snapshot_question["type"] == Question.Type.MULTI_SELECT:
        total_correct = len(correct_ids) or 1
        correct_selected = len(selected_choice_ids & correct_ids)
        incorrect_selected = len(selected_choice_ids - correct_ids)
        fraction = max(0, correct_selected - incorrect_selected) / total_correct
        fraction = min(fraction, 1.0)
        is_correct = selected_choice_ids == correct_ids
        return is_correct, fraction

    # MCQ / TRUE_FALSE — binary
    is_correct = selected_choice_ids == correct_ids
    return is_correct, (1.0 if is_correct else 0.0)


@transaction.atomic
def save_answer(attempt: Attempt, question_id: int, selected_choice_ids: list[int]) -> AttemptAnswer:
    if not attempt.is_in_progress:
        raise ValueError("This attempt is already submitted.")

    snapshot_question = _get_snapshot_question(attempt, question_id)
    if snapshot_question is None:
        raise ValueError("That question is not part of this attempt.")

    selected_set = set(selected_choice_ids)
    is_correct, _fraction = _grade_question(snapshot_question, selected_set)

    answer, _created = AttemptAnswer.objects.update_or_create(
        attempt=attempt,
        question_id=question_id,
        defaults={"is_correct": is_correct},
    )
    # Choice rows referenced by id must actually exist and belong to
    # this question — defensive against a tampered client payload.
    valid_choices = Choice.objects.filter(id__in=selected_set, question_id=question_id)
    answer.selected_choices.set(valid_choices)
    return answer


@transaction.atomic
def finalize_attempt(attempt: Attempt) -> Attempt:
    if not attempt.is_in_progress:
        return attempt

    answers_by_question = {a.question_id: a for a in attempt.answers.all()}

    total_fraction = 0.0
    for sq in attempt.question_snapshot:
        existing = answers_by_question.get(sq["question_id"])
        if existing:
            selected_ids = set(existing.selected_choices.values_list("id", flat=True))
            _is_correct, fraction = _grade_question(sq, selected_ids)
        else:
            fraction = 0.0  # unanswered — counts as incorrect, not a blocker
        total_fraction += fraction

    question_count = len(attempt.question_snapshot) or 1
    score_percent = round(total_fraction * 100 / question_count)

    attempt.score_percent = score_percent
    attempt.passed = score_percent >= attempt.quiz.pass_mark
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["score_percent", "passed", "submitted_at"])

    if attempt.passed:
        # A passing module quiz can unlock the next module; a passing
        # final quiz can complete the course. Both are cheap to check
        # unconditionally — is_course_complete() just returns False
        # if the rest isn't ready yet. Local import: enrollment
        # imports this module too (is_module_completed/is_course_complete),
        # so this stays a function-level import to avoid a load-order
        # cycle between the two apps' services modules.
        from apps.enrollment.services import _mark_enrollment_completed_if_ready

        _mark_enrollment_completed_if_ready(attempt.enrollment)

    return attempt


def expire_attempt_if_stale(attempt: Attempt) -> Attempt:
    """Call at the top of any view that touches an in-progress attempt
    — the reactive path, catches an attempt the moment its owner comes
    back to it."""
    if attempt.is_expired:
        return finalize_attempt(attempt)
    return attempt


def expire_all_stale_attempts() -> int:
    """The proactive path — build spec §5's `expire_stale_attempts`
    Celery task (every 15 min, Phase 7) calls this. Finalizes every
    in-progress attempt past its expires_at platform-wide, not just
    the one a view happens to touch, so a learner who simply never
    comes back still gets graded on what they'd answered rather than
    leaving the attempt open forever. Returns the count finalized."""
    from django.utils import timezone

    stale = Attempt.objects.filter(submitted_at__isnull=True, expires_at__isnull=False, expires_at__lte=timezone.now())
    count = 0
    for attempt in stale:
        finalize_attempt(attempt)
        count += 1
    return count
