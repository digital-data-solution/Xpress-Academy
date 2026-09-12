"""Shared standard-competition ranking (1, 2, 2, 4) — build spec §C:
"cohort ranking within a school." Used by both the live school
dashboard (views.py::school_dashboard) and the diagnostic's PDF school
summary (pdf.py::build_school_summary_pdf) so the same tie-handling
rule applies everywhere a proprietor sees a ranked list, not
duplicated inline in each place.

A tied pair shares a rank rather than being silently split apart by
list order (which would falsely imply one beat the other) — the next
distinct score after a tie resumes at its true position (1, 2, 2, 4,
not 1, 2, 2, 3), so the rank number always means "this many people
scored strictly higher," which is what "ranked #1 of 20" is supposed
to promise.
"""


def rank_by_score(items, score_fn):
    """Returns [(item, rank), ...] sorted by descending score_fn(item)."""
    ranked = sorted(items, key=lambda item: -score_fn(item))
    result = []
    rank, previous_score = 0, None
    for i, item in enumerate(ranked, start=1):
        score = score_fn(item)
        if score != previous_score:
            rank = i
            previous_score = score
        result.append((item, rank))
    return result
