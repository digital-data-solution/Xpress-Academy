"""Thin wrapper around load_verified_questions, fixed to the WAEC
Chemistry parameters. See load_verified_questions for the generic
logic. WAEC Chemistry's syllabus (15 topics, one section) is uniform
across every WAEC member country — no country-specific split needed."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads waec_chemistry_59_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "waec_chemistry_59_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="waec",
            exam_name="WAEC (WASSCE)",
            exam_description="West African Examinations Council's West African Senior School Certificate Examination.",
            subject="Chemistry",
            bank_name="WAEC — Chemistry",
            bank_description="AI-generated, independently blind-verified WAEC Chemistry question bank.",
        )
