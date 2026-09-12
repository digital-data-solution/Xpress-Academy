"""Thin wrapper around create_diagnostic, fixed to the WAEC Biology
parameters. See create_diagnostic for the actual generic logic."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Creates the public WAEC Biology diagnostic mock test (/diagnostic/waec-biology-diagnostic/)."

    def handle(self, *args, **options):
        call_command(
            "create_diagnostic",
            bank_name="WAEC — Biology",
            slug="waec-biology-diagnostic",
            title="Free WAEC Biology Diagnostic",
            question_count=20,
            time_limit_minutes=30,
        )
