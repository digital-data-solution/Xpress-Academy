"""Thin wrapper around load_verified_questions, fixed to the JAMB
Physics parameters. See load_verified_questions for the generic logic."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads jamb_physics_84_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "jamb_physics_84_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="jamb",
            exam_name="JAMB UTME",
            exam_description="Nigeria's Joint Admissions and Matriculation Board Unified Tertiary Matriculation Examination.",
            subject="Physics",
            bank_name="JAMB — Physics",
            bank_description="AI-generated, independently blind-verified JAMB UTME Physics question bank.",
        )
