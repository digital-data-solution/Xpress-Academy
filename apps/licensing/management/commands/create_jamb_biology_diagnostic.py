"""Creates (or confirms) the public, shareable free JAMB Biology
diagnostic — the outbound door-opener, build spec §B. A one-off setup
command, not something run repeatedly: the diagnostic's own model
already existed and was fully tested before this, but no real instance
pointing at the verified JAMB Biology bank had ever actually been
created in any database, dev or prod — this closes that gap.

Idempotent: get_or_create by slug, safe to re-run (e.g. against prod
via the standard local-workflow-against-prod-DATABASE_URL pattern)."""

from django.core.management.base import BaseCommand, CommandError

from apps.assessment.models import QuestionBank
from apps.licensing.models import DiagnosticMockTest
from apps.organizations.models import Organization

SLUG = "jamb-biology-diagnostic"
QUESTION_COUNT = 20  # a real mock-length diagnostic, not the full 100 — free and inviting, not a slog


class Command(BaseCommand):
    help = "Creates the public JAMB Biology diagnostic mock test (/diagnostic/jamb-biology-diagnostic/)."

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            raise CommandError("Organization 'xpress-digital-academy' not found — run this against a real seeded DB.")

        bank = QuestionBank.objects.filter(organization=org, name="JAMB — Biology").first()
        if not bank:
            raise CommandError("QuestionBank 'JAMB — Biology' not found — run load_jamb_biology_100 first.")

        test, created = DiagnosticMockTest.objects.get_or_create(
            slug=SLUG,
            defaults={
                "organization": org,
                "title": "Free JAMB Biology Diagnostic",
                "bank": bank,
                "question_count": QUESTION_COUNT,
                "time_limit_minutes": 30,
                "is_active": True,
            },
        )
        verb = "Created" if created else "Already exists"
        self.stdout.write(self.style.SUCCESS(f"{verb} — live at /diagnostic/{test.slug}/ (id={test.pk})"))
