"""Thin wrapper around load_verified_questions, fixed to the Nigerian
civil service General Knowledge parameters — question-bank-engine
build spec §D, the second exam ported after JAMB and WAEC.

Real scope narrowing, decided with the user: civil service recruitment
exams have no single official published syllabus (unlike JAMB/WAEC),
and are aptitude-test-style (Verbal Reasoning, Numerical Reasoning,
General Knowledge, Current Affairs) rather than a subject curriculum.
Only the General Knowledge slice — Nigerian civics, government
structure, history, geography — is covered here, since it's the only
part that (a) has real, sourceable, stable facts and (b) fits the
existing recall-MCQ format. Verbal/Numerical Reasoning (number series,
analogies, data interpretation) would need a different question format
this platform doesn't support yet. "Current affairs" is deliberately
excluded too — those facts go stale by design, unlike civics/history/
geography, which are far more durable (though even durable-seeming
facts weren't perfectly safe here: two questions in this very set were
caught and fixed for being outdated — the national anthem and the
official Democracy Day date both changed in the last few years — a
reminder that "durable" general knowledge still needs the same
independent-verification discipline as anything else)."""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Loads civil_service_gk_97_verified.json into real Question/Choice rows. (Wrapper around load_verified_questions.)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "civil_service_gk_97_verified.json"),
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
                "commissions — General Knowledge slice only; see this command's own docstring for scope."
            ),
            subject="General Knowledge",
            bank_name="Civil Service — General Knowledge",
            bank_description=(
                "AI-generated, independently blind-verified Nigerian civics/government/history/geography "
                "question bank for civil service recruitment exam prep (General Knowledge component only)."
            ),
        )
