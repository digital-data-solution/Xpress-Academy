"""Thin wrapper around load_verified_questions, fixed to the WAEC
Physics parameters. See load_verified_questions for the generic logic.

Unlike WAEC Biology, WAEC Physics's syllabus is uniform across every
WAEC member country (Nigeria, Ghana, Sierra Leone, Gambia, Liberia) —
no country-specific section split needed here."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads waec_physics_70_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "waec_physics_70_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="waec",
            exam_name="WAEC (WASSCE)",
            exam_description="West African Examinations Council's West African Senior School Certificate Examination.",
            subject="Physics",
            bank_name="WAEC — Physics",
            bank_description="AI-generated, independently blind-verified WAEC Physics question bank.",
        )
