"""Thin wrapper around load_verified_questions, fixed to the JAMB
English parameters. Real scope note: JAMB's Use of English paper also
includes Comprehension and Summary sections (a passage + several
linked questions), which this bank deliberately excludes — the
existing Question model's single, standalone stem has no way to
attach a shared passage, the same reasoning WAEC English's Essay/
Comprehension papers were excluded for. Only Lexis & Structure
(grammar, vocabulary, idioms, punctuation) and Oral English
(pronunciation: vowel sounds, consonants, rhymes, word stress) are
covered here — both fit the existing standalone-MCQ format cleanly.

See load_verified_questions for the generic loading logic."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads jamb_english_50_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "jamb_english_50_verified.json"),
            help="Path to the verified questions JSON.",
        )

    def handle(self, *args, **options):
        call_command(
            "load_verified_questions",
            file=options["file"],
            exam_code="jamb",
            exam_name="JAMB UTME",
            exam_description="Nigeria's Joint Admissions and Matriculation Board Unified Tertiary Matriculation Examination.",
            subject="English",
            bank_name="JAMB — English",
            bank_description=(
                "AI-generated, independently blind-verified JAMB UTME English question bank "
                "(Lexis & Structure + Oral English — Comprehension/Summary excluded, no passage-attachment support yet)."
            ),
        )
