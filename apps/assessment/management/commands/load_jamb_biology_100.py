"""Loads the 100 verified JAMB Biology questions (question-bank-engine
Phase A first deliverable) from jamb_biology_100_verified.json into the
real Question/Choice/SourceExam/SyllabusTopic models.

Idempotent — re-running updates existing rows (matched by stem, since
these questions have no other natural key) rather than duplicating.
Safe to re-run after fixing a typo in the source JSON.

Every question here was independently re-solved blind (stem+options
only, no stored answer key visible) by a separate agent process before
this command ever runs — see the source file's own "verified" /
"verification_note" fields. This command trusts that already-done
verification and sets verification_status=VERIFIED directly; it does
NOT re-verify, since re-verification only means something the first
time, before a human or this command has seen the stored key."""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, SourceExam, SyllabusTopic
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Loads jamb_biology_100_verified.json into real Question/Choice rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=str(Path(settings.BASE_DIR) / "apps" / "assessment" / "data" / "jamb_biology_100_verified.json"),
            help="Path to the verified questions JSON.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"{path} does not exist.")

        with open(path, encoding="utf-8") as f:
            questions_data = json.load(f)

        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            raise CommandError("Organization 'xpress-digital-academy' not found — run this against a real seeded DB.")

        source_exam, _ = SourceExam.objects.get_or_create(
            code="jamb",
            defaults={
                "name": "JAMB UTME",
                "description": "Nigeria's Joint Admissions and Matriculation Board Unified Tertiary Matriculation Examination.",
            },
        )

        bank, _ = QuestionBank.objects.get_or_create(
            organization=org, name="JAMB — Biology",
            defaults={"description": "AI-generated, independently blind-verified JAMB UTME Biology question bank."},
        )

        # SyllabusTopic rows: get_or_create per (source_exam, subject, name)
        # section is stored but not part of the uniqueness key — two
        # questions in the same named topic always share one row.
        topic_cache = {}

        def get_topic(section: str, name: str) -> SyllabusTopic:
            key = (section, name)
            if key not in topic_cache:
                topic, _ = SyllabusTopic.objects.get_or_create(
                    source_exam=source_exam, subject="Biology", name=name,
                    defaults={"section": section},
                )
                topic_cache[key] = topic
            return topic_cache[key]

        created, updated = 0, 0
        for q in questions_data:
            topic = get_topic(q["section"], q["topic"])

            question, was_created = Question.objects.update_or_create(
                bank=bank, stem=q["stem"],
                defaults={
                    "type": Question.Type.MCQ,
                    "explanation": q["explanation"],
                    "difficulty": q["difficulty"],
                    "source_exam": source_exam,
                    "is_ai_generated": True,
                    "verification_status": "VERIFIED" if q.get("verified") else "N_A",
                    "is_active": True,
                },
            )
            question.syllabus_topics.set([topic])

            # Replace choices cleanly rather than trying to diff them —
            # this command only ever loads from a known-good source file,
            # never edits a hand-tweaked admin question (those wouldn't
            # match by stem to anything in this file in the first place).
            question.choices.all().delete()
            for i, (letter, text) in enumerate(q["options"].items()):
                Choice.objects.create(
                    question=question, text=text, is_correct=(letter == q["correct"]), order=i,
                )

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done — {created} question(s) created, {updated} updated, "
            f"{len(topic_cache)} syllabus topic(s), bank '{bank.name}'."
        ))
