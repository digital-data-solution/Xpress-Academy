"""Thin wrapper around load_verified_questions, fixed to the Civil
Service Public Service Rules (PSR) parameters. See load_verified_questions
for the generic logic.

Source: the user's own hard copy of the Federal Government Public
Service Rules (2021 edition), cross-checked against the official soft
copy at oagf.gov.ng. Unlike a curriculum-based syllabus (JAMB/WAEC),
the PSR is a single, stable, official government document — content is
transcribed directly from scanned page images (the official copy has
no text layer), then blind-verified question-by-question against the
real transcribed rule text, not against general reasoning about what
a civil service rulebook "probably" says.

Built incrementally, chapter by chapter, given the document's real
size (17 chapters, ~500 rules). This file currently loads Chapters 1-2
(Introduction; Appointments and Leaving the Service, 48 questions);
later chapters extend the same bank via re-runnable follow-up files as
they're verified, matching the "one bank, grows over time" pattern
already used elsewhere on this platform."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads civil_service_psr_ch1_2_48_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "civil_service_psr_ch1_2_48_verified.json"),
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
                "commissions — Public Service Rules slice only; see this command's own docstring for scope."
            ),
            subject="Public Service Rules",
            bank_name="Civil Service — Public Service Rules",
            bank_description=(
                "AI-generated, independently blind-verified question bank on the Federal Government Public "
                "Service Rules (2021) — sourced from the real document text, not general reasoning. "
                "Currently covers Chapters 1-2; more chapters added as they're verified."
            ),
        )
