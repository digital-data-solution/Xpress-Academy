"""Bulk question import from CSV — build spec §8 Phase 4 deliverable:
"Admin bulk-import of questions from CSV."

Expected columns (header row required, extra columns ignored):
  stem, type, difficulty, explanation, topics, source_note,
  choice_1, choice_1_correct, choice_2, choice_2_correct,
  choice_3, choice_3_correct, choice_4, choice_4_correct

- type: MCQ | MULTI_SELECT | TRUE_FALSE (case-insensitive)
- difficulty: EASY | MEDIUM | HARD (case-insensitive, defaults MEDIUM)
- topics: semicolon-separated topic names — created if they don't exist
- choice_correct columns: TRUE/FALSE/1/0/yes/no (case-insensitive)
- up to 4 choices; TRUE_FALSE only needs 2, MULTI_SELECT can have >1 correct

This format is deliberately spreadsheet-friendly — it's meant to be
filled in Excel/Google Sheets (matching how the course-content briefs
already ask for quiz questions with explanations) and exported as CSV,
not hand-written.
"""

import csv
import io
from dataclasses import dataclass, field

from django.db import transaction

from .models import Choice, Question, QuestionBank, Topic

VALID_TYPES = {c[0] for c in Question.Type.choices}
VALID_DIFFICULTIES = {c[0] for c in Question.Difficulty.choices}
TRUTHY = {"true", "1", "yes", "y"}


@dataclass
class ImportResult:
    created: int = 0
    errors: list[str] = field(default_factory=list)


def _parse_bool(value: str) -> bool:
    return (value or "").strip().lower() in TRUTHY


def import_questions_from_csv(bank: QuestionBank, file_obj) -> ImportResult:
    result = ImportResult()
    raw = file_obj.read()
    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        result.errors.append("File appears to be empty or not a CSV.")
        return result

    required = {"stem", "type"}
    missing = required - set(f.strip() for f in reader.fieldnames)
    if missing:
        result.errors.append(f"Missing required column(s): {', '.join(sorted(missing))}")
        return result

    with transaction.atomic():
        for i, row in enumerate(reader, start=2):  # row 1 is the header
            stem = (row.get("stem") or "").strip()
            if not stem:
                continue  # silently skip blank rows

            qtype = (row.get("type") or "").strip().upper()
            if qtype not in VALID_TYPES:
                result.errors.append(f"Row {i}: invalid type '{qtype}' — skipped.")
                continue

            difficulty = (row.get("difficulty") or "MEDIUM").strip().upper()
            if difficulty not in VALID_DIFFICULTIES:
                difficulty = Question.Difficulty.MEDIUM

            choice_pairs = []
            for n in range(1, 5):
                ctext = (row.get(f"choice_{n}") or "").strip()
                if not ctext:
                    continue
                is_correct = _parse_bool(row.get(f"choice_{n}_correct"))
                choice_pairs.append((ctext, is_correct))

            if len(choice_pairs) < 2:
                result.errors.append(f"Row {i}: needs at least 2 choices — skipped.")
                continue

            correct_count = sum(1 for _, c in choice_pairs if c)
            if qtype in (Question.Type.MCQ, Question.Type.TRUE_FALSE) and correct_count != 1:
                result.errors.append(
                    f"Row {i}: {qtype} needs exactly one correct choice, found {correct_count} — skipped."
                )
                continue
            if qtype == Question.Type.MULTI_SELECT and correct_count < 1:
                result.errors.append(f"Row {i}: MULTI_SELECT needs at least one correct choice — skipped.")
                continue

            question = Question.objects.create(
                bank=bank,
                type=qtype,
                stem=stem,
                explanation=(row.get("explanation") or "").strip(),
                difficulty=difficulty,
                source_note=(row.get("source_note") or "").strip(),
            )
            for order, (ctext, is_correct) in enumerate(choice_pairs, start=1):
                Choice.objects.create(question=question, text=ctext, is_correct=is_correct, order=order)

            topic_names = [t.strip() for t in (row.get("topics") or "").split(";") if t.strip()]
            for name in topic_names:
                topic, _ = Topic.objects.get_or_create(name=name)
                question.topics.add(topic)

            result.created += 1

    return result
