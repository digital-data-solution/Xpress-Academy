"""Generic diagnostic-setup command — question-bank-engine build spec
§D's "reuse the same generation, verification and delivery code" rule
applies here too, not just to the loader. Creates (or confirms) a
public, shareable DiagnosticMockTest pointing at an existing
QuestionBank. A one-off setup command, not run repeatedly per bank.

Idempotent: get_or_create by slug, safe to re-run (e.g. against prod
via the standard local-workflow-against-prod-DATABASE_URL pattern).

create_jamb_biology_diagnostic and create_waec_biology_diagnostic are
thin wrappers around this with their bank/title/slug fixed, same
wrapper pattern as load_verified_questions's own callers."""

from django.core.management.base import BaseCommand, CommandError

from apps.assessment.models import QuestionBank
from apps.licensing.models import DiagnosticMockTest
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Creates a public diagnostic mock test pointing at an existing QuestionBank."

    def add_arguments(self, parser):
        parser.add_argument("--bank-name", required=True, help="Exact QuestionBank.name, e.g. 'WAEC — Biology'.")
        parser.add_argument("--slug", required=True, help="URL slug, e.g. 'waec-biology-diagnostic'.")
        parser.add_argument("--title", required=True, help="Public title, e.g. 'Free WAEC Biology Diagnostic'.")
        parser.add_argument("--question-count", type=int, default=20, help="Questions per attempt (default 20).")
        parser.add_argument("--time-limit-minutes", type=int, default=30, help="Time limit in minutes (default 30).")
        parser.add_argument(
            "--org-slug", default="xpress-digital-academy", help="Organization.slug that owns the diagnostic."
        )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug=options["org_slug"]).first()
        if not org:
            raise CommandError(f"Organization '{options['org_slug']}' not found — run this against a real seeded DB.")

        bank = QuestionBank.objects.filter(organization=org, name=options["bank_name"]).first()
        if not bank:
            raise CommandError(f"QuestionBank '{options['bank_name']}' not found — load its questions first.")

        test, created = DiagnosticMockTest.objects.get_or_create(
            slug=options["slug"],
            defaults={
                "organization": org,
                "title": options["title"],
                "bank": bank,
                "question_count": options["question_count"],
                "time_limit_minutes": options["time_limit_minutes"],
                "is_active": True,
            },
        )
        verb = "Created" if created else "Already exists"
        self.stdout.write(self.style.SUCCESS(f"{verb} — live at /diagnostic/{test.slug}/ (id={test.pk})"))
