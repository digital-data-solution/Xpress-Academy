"""Generic verified-question loader — question-bank-engine build spec
§D: "Make SourceExam a first-class dimension so TRCN PQE, WAEC and
civil service banks reuse the same generation, verification and
delivery code. Do not fork." Loads a JSON file of independently
blind-verified questions into the real Question/Choice/SourceExam/
SyllabusTopic models, for any exam and subject — added when WAEC
Biology followed JAMB Biology, rather than copy-pasting a second
near-identical command. load_jamb_biology_100 is now a thin wrapper
around this with JAMB's parameters fixed, kept for backward
compatibility with its existing name.

Idempotent — re-running updates existing rows (matched by bank+stem,
since these questions have no other natural key) rather than
duplicating. Safe to re-run after fixing a typo in the source JSON.

Every question in the source file was independently re-solved blind
(stem+options only, no stored answer key visible) by a separate agent
process before this command ever runs — see the source file's own
"verified"/"verification_note" fields. This command trusts that
already-done verification and sets verification_status=VERIFIED
directly; it does NOT re-verify, since re-verification only means
something the first time, before a human or this command has seen the
stored key.
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, SourceExam, SyllabusTopic
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Loads a verified-questions JSON file into real Question/Choice rows, for any exam/subject."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the verified questions JSON.")
        parser.add_argument("--exam-code", required=True, help="SourceExam.code, e.g. 'jamb', 'waec'.")
        parser.add_argument("--exam-name", required=True, help="SourceExam.name, e.g. 'JAMB UTME'.")
        parser.add_argument(
            "--exam-description", default="", help="SourceExam.description — only used the first time this exam is created."
        )
        parser.add_argument("--subject", required=True, help="SyllabusTopic.subject, e.g. 'Biology'.")
        parser.add_argument("--bank-name", required=True, help="QuestionBank.name, e.g. 'WAEC — Biology'.")
        parser.add_argument(
            "--bank-description", default="", help="QuestionBank.description — only used the first time this bank is created."
        )
        parser.add_argument(
            "--org-slug", default="xpress-digital-academy", help="Organization.slug that owns the bank."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"{path} does not exist.")

        with open(path, encoding="utf-8") as f:
            questions_data = json.load(f)

        org = Organization.objects.filter(slug=options["org_slug"]).first()
        if not org:
            raise CommandError(f"Organization '{options['org_slug']}' not found — run this against a real seeded DB.")

        source_exam, _ = SourceExam.objects.get_or_create(
            code=options["exam_code"],
            defaults={"name": options["exam_name"], "description": options["exam_description"]},
        )

        bank, _ = QuestionBank.objects.get_or_create(
            organization=org, name=options["bank_name"],
            defaults={"description": options["bank_description"]},
        )

        subject = options["subject"]
        # SyllabusTopic rows: get_or_create per (source_exam, subject, name)
        # — section is stored but not part of the uniqueness key, so two
        # questions in the same named topic always share one row.
        topic_cache = {}

        def get_topic(section: str, name: str) -> SyllabusTopic:
            key = (section, name)
            if key not in topic_cache:
                topic, _ = SyllabusTopic.objects.get_or_create(
                    source_exam=source_exam, subject=subject, name=name,
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
            # this command only ever loads from a known-good source
            # file, never edits a hand-tweaked admin question (those
            # wouldn't match by stem to anything in this file anyway).
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
