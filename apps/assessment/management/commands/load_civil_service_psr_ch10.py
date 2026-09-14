"""Thin wrapper around load_verified_questions for PSR Chapter 10
(Discipline) — the largest chapter in the document (7 sections, ~44
rules, pages 68-88). A follow-up to load_civil_service_psr.py
(Chapters 1-2) and the Chapter 3-9 follow-ups, extending the same
bank. See load_civil_service_psr for the full sourcing/verification
writeup; same discipline: 51 questions transcribed from the real
scanned document, each independently blind-verified by two reviewers
with no shared context (one automated subagent, one direct cross-check
against the source transcript) against the actual rule text, not
general reasoning. Given the chapter's real size, verification itself
was split into two sequential subagent batches (26 + 25 questions,
run one at a time, not in parallel) rather than one large call.

Safe to re-run — load_verified_questions matches by (bank, stem), so
this only ever creates or updates these 51 questions."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads civil_service_psr_ch10_51_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "civil_service_psr_ch10_51_verified.json"),
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
                "Currently covers Chapters 1-10; more chapters added as they're verified."
            ),
        )
