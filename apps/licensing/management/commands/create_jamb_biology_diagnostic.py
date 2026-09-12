"""Thin wrapper around create_diagnostic, fixed to the JAMB Biology
parameters — kept as its own command name since it's the one already
used in the original rollout. See create_diagnostic for the actual
generic logic (extracted when the WAEC Biology diagnostic followed,
per the same "do not fork" reasoning as load_verified_questions)."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates the public JAMB Biology diagnostic mock test (/diagnostic/jamb-biology-diagnostic/)."

    def handle(self, *args, **options):
        call_command(
            "create_diagnostic",
            bank_name="JAMB — Biology",
            slug="jamb-biology-diagnostic",
            title="Free JAMB Biology Diagnostic",
            question_count=20,
            time_limit_minutes=30,
        )
