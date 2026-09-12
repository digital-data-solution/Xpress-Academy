"""Thin, backward-compatible wrapper around load_verified_questions,
fixed to the JAMB Biology parameters — kept as its own command name
since it's the one already used in the original Phase A rollout. See
load_verified_questions for the actual generic logic (extracted when
WAEC Biology followed JAMB Biology, per the spec's own "do not fork"
rule for SourceExam reuse — this file used to contain that logic
directly)."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads jamb_biology_100_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "jamb_biology_100_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="jamb",
            exam_name="JAMB UTME",
            exam_description="Nigeria's Joint Admissions and Matriculation Board Unified Tertiary Matriculation Examination.",
            subject="Biology",
            bank_name="JAMB — Biology",
            bank_description="AI-generated, independently blind-verified JAMB UTME Biology question bank.",
        )
