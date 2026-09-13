"""Wraps an existing, verified QuestionBank into a real, licensable
Course + FINAL Quiz — the missing link between the question-bank
engine and actual revenue. Question banks and free diagnostics existed
with no way for an institution to actually license full access to
them: InstitutionalLicense.courses points at catalog.Course, and until
this command, none of the exam banks (JAMB/WAEC Biology, Civil Service
GK, JAMB Physics, ...) had a Course or Quiz at all — a school could
not license "full JAMB access" no matter how much content existed.

Deliberately a bare Course with zero lessons/modules: an exam-prep
"course" here IS the question bank — there's no separate lesson
content to gate the final quiz behind, and none is needed. This
required a real fix in enrollment.services.all_lessons_completed,
which previously returned False (not vacuously True) for a course
with zero lessons — never exercised before since every real course
had lessons, but it would have made this course's FINAL quiz
permanently inaccessible. Fixed at the source rather than worked
around here.

pricing_model=PAID by design, not institution-only: an individual can
also buy direct access through the normal checkout flow with zero
extra code (Payment/Paystack already handles any PAID course) — the
institutional path (InstitutionalLicense.courses) is additive on top
of that, not a replacement for it.

Created UNPUBLISHED (review_status stays DRAFT) — a real, DB-enforced
constraint (course_publish_requires_approved_review_status) requires
review_status=APPROVED before is_published can be True, which itself
requires a Vertical with a domain_reviewer assigned. This command has
no legitimate way to satisfy that (it isn't a real domain reviewer),
and won't fake it. Institutional licensing still works exactly as
intended despite being unpublished: InstitutionalLicense/
bulk_enroll_students_from_csv create Enrollment rows directly, never
going through the public catalog or checkout, so is_published is
irrelevant to that path. Only the individual-direct-purchase path
(browsing the public catalog, checkout) needs someone to actually run
this course through the real review process first."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Quiz, QuestionBank
from apps.catalog.models import Audience, Course, Programme
from apps.organizations.models import Organization


class Command(BaseCommand):
    help = "Wraps a QuestionBank into a real, licensable Course + FINAL Quiz."

    def add_arguments(self, parser):
        parser.add_argument("--bank-name", required=True, help="Exact QuestionBank.name, e.g. 'JAMB — Biology'.")
        parser.add_argument("--slug", required=True, help="Course slug, e.g. 'jamb-biology-exam-prep'.")
        parser.add_argument("--title", required=True, help="Course title, e.g. 'JAMB UTME Biology Exam Prep'.")
        parser.add_argument("--question-count", type=int, default=40, help="Questions per exam attempt (default 40).")
        parser.add_argument("--time-limit-minutes", type=int, default=40, help="Time limit in minutes (default 40).")
        parser.add_argument("--pass-mark", type=int, default=50, help="Pass mark percent (default 50).")
        parser.add_argument("--price-ngn", type=int, default=5000, help="Individual direct-purchase price (default 5000).")
        parser.add_argument(
            "--programme-title", default="Exam Preparation", help="Programme this course belongs under."
        )
        parser.add_argument(
            "--org-slug", default="xpress-digital-academy", help="Organization.slug that owns the course."
        )

    @transaction.atomic
    def handle(self, *args, **options):
        org = Organization.objects.filter(slug=options["org_slug"]).first()
        if not org:
            raise CommandError(f"Organization '{options['org_slug']}' not found — run this against a real seeded DB.")

        bank = QuestionBank.objects.filter(organization=org, name=options["bank_name"]).first()
        if not bank:
            raise CommandError(f"QuestionBank '{options['bank_name']}' not found — load its questions first.")

        programme, _ = Programme.objects.get_or_create(
            organization=org, title=options["programme_title"],
            defaults={"audience": Audience.GENERAL},
        )

        course, created = Course.objects.get_or_create(
            slug=options["slug"],
            defaults={
                "organization": org,
                "programme": programme,
                "title": options["title"],
                "audience": Audience.GENERAL,
                "pricing_model": Course.PricingModel.PAID,
                "price_ngn": options["price_ngn"],
                # NOT published — see module docstring. Institutional
                # licensing doesn't need it; individual direct-purchase
                # does, once someone runs it through the real review
                # process (assign a Vertical with a domain_reviewer,
                # move review_status to APPROVED, then publish).
                "is_published": False,
            },
        )

        quiz, quiz_created = Quiz.objects.get_or_create(
            scope=Quiz.Scope.FINAL, course=course,
            defaults={
                "title": options["title"],
                "bank": bank,
                "question_count": options["question_count"],
                "time_limit_minutes": options["time_limit_minutes"],
                "pass_mark": options["pass_mark"],
                "max_attempts": 0,
            },
        )

        course_verb = "Created" if created else "Already existed"
        quiz_verb = "Created" if quiz_created else "Already existed"
        self.stdout.write(self.style.SUCCESS(
            f"{course_verb} course '{course.title}' (id={course.pk}, slug={course.slug}), "
            f"{quiz_verb.lower()} its FINAL quiz against bank '{bank.name}' — "
            f"ready to add to an InstitutionalLicense.courses right now. "
            f"NOT published — individual direct-purchase needs a Vertical + reviewer "
            f"approval first (see this command's docstring)."
        ))
