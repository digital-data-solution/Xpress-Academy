"""Thin wrapper around load_verified_questions, fixed to the Nigerian
civil service Numerical Reasoning parameters. See load_verified_questions
for the generic logic, and load_civil_service_verbal for the fuller
scope-correction note (same reasoning applies here: standalone
numerical items fit the existing MCQ engine, only chart/table-based
"data interpretation" sets are excluded).

Covers number series, ratio & proportion, percentages, averages,
simple interest, profit & loss, speed-distance-time, fractions &
decimals, basic algebra, HCF/LCM, and approximation -- all
single-stem, self-contained MCQs. Excludes data-interpretation
question sets that share one chart/table across several questions,
same reasoning as every other passage/figure-sharing exclusion on
this platform."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads civil_service_numerical_50_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "civil_service_numerical_50_verified.json"),
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
                "commissions — Numerical Reasoning slice only; see this command's own docstring for scope."
            ),
            subject="Numerical Reasoning",
            bank_name="Civil Service — Numerical Reasoning",
            bank_description=(
                "AI-generated, independently blind-verified Numerical Reasoning question bank (number "
                "series, ratios, percentages, averages, simple interest, profit & loss, speed-distance-time, "
                "fractions, basic algebra, HCF/LCM, approximation) for civil service recruitment exam prep."
            ),
        )
