"""Thin wrapper around load_verified_questions, fixed to the WAEC
Biology parameters — question-bank-engine build spec §D, the first
exam ported after JAMB. Scope note: Nigeria-relevant WAEC syllabus
sections only (Section A, common to all countries, + Section C,
Nigeria/Sierra Leone/Gambia/Liberia) — Section B is Ghana-only and
deliberately out of scope, confirmed with the user before any
question was generated."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads waec_biology_100_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "waec_biology_100_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="waec",
            exam_name="WAEC (WASSCE)",
            exam_description="West African Examinations Council's West African Senior School Certificate Examination.",
            subject="Biology",
            bank_name="WAEC — Biology",
            bank_description=(
                "AI-generated, independently blind-verified WAEC Biology question bank "
                "(Section A + Section C — Nigeria-relevant scope, Section B/Ghana excluded)."
            ),
        )
