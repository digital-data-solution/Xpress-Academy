"""Thin wrapper around load_verified_questions, fixed to the WAEC
English Language parameters. See load_verified_questions for the
generic logic.

Scope note: this bank covers WAEC English's objective-test material
only -- Paper 1 (Lexis & Structure) and the Nigeria/Liberia "Test of
Orals" variant of Paper 3 (Oral English: vowel/consonant sounds,
stress, rhymes, intonation). It deliberately excludes Paper 2 (Essay,
Comprehension, Summary) since those require a shared reading passage
per question, which the single-stem Question/Choice MCQ model used
throughout this engine does not support. It also excludes the
Ghana/Gambia/Sierra Leone "Listening Comprehension" variant of Paper 3
(different skill, different format) in favour of the Nigeria variant,
matching this platform's primary market.
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads waec_english_50_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "waec_english_50_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="waec",
            exam_name="WAEC (WASSCE)",
            exam_description="West African Examinations Council's West African Senior School Certificate Examination.",
            subject="English Language",
            bank_name="WAEC — English Language",
            bank_description="AI-generated, independently blind-verified WAEC English Language question bank (Lexis, Structure, Oral English -- Nigeria variant).",
        )
