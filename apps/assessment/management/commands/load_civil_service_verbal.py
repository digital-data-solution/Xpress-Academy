"""Thin wrapper around load_verified_questions, fixed to the Nigerian
civil service Verbal Reasoning parameters. See load_verified_questions
for the generic logic, and load_civil_service_gk for the exam-level
scope background.

Correction to load_civil_service_gk's own docstring: it originally
said Verbal/Numerical Reasoning "would need a different question
format this platform doesn't support yet." That turned out to be too
pessimistic -- only chart/table-based "data interpretation" item SETS
(several questions sharing one figure) need a shared-passage feature
this platform lacks, the same limitation that excludes JAMB/WAEC
English Comprehension. Standalone Verbal Reasoning items (synonyms,
antonyms, analogies, classification/odd-one-out, sentence completion,
coding-decoding, logical deduction, letter series) are all
single-stem MCQs and fit the existing engine cleanly -- this bank
covers exactly that, and is universal aptitude-test content (the same
item taxonomy used across Nigerian, UK, and other civil service
screening exams), not a country-specific curriculum document, so no
separate syllabus-sourcing step was needed the way JAMB/WAEC/TRCN
require."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads civil_service_verbal_50_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "civil_service_verbal_50_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="civil-service-ng",
            exam_name="Nigerian Civil Service Recruitment Exam",
            exam_description=(
                "General recruitment exams administered by Nigerian federal/state civil service "
                "commissions — Verbal Reasoning slice only; see this command's own docstring for scope."
            ),
            subject="Verbal Reasoning",
            bank_name="Civil Service — Verbal Reasoning",
            bank_description=(
                "AI-generated, independently blind-verified Verbal Reasoning question bank (synonyms, "
                "antonyms, analogies, classification, sentence completion, coding-decoding, logical "
                "deduction, letter series) for civil service recruitment exam prep."
            ),
        )
