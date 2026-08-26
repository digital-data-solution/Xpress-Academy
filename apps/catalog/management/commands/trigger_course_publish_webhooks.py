from django.core.management.base import BaseCommand

from apps.catalog.models import Course, Programme
from apps.catalog.webhooks import notify_course_published


class Command(BaseCommand):
    help = (
        "Manually re-fires the course-publish webhook for every currently "
        "published course whose Programme has a real webhook_line (DIGITAL "
        "or VET) — for courses that were published before the webhook "
        "existed/was configured, since Course.save() only fires it on the "
        "actual draft->published transition, not on a course that's "
        "already published. Safe to target a specific course via --slug; "
        "otherwise fires for every eligible published course. Each run "
        "creates a fresh draft on the receiving side, so don't run this "
        "repeatedly without reason once it's already fired."
    )

    def add_arguments(self, parser):
        parser.add_argument("--slug", help="Only fire for this course's slug, not every eligible course.")

    def handle(self, *args, **options):
        courses = Course.objects.filter(
            is_published=True,
        ).exclude(programme__webhook_line=Programme.WebhookLine.NONE).select_related("programme")

        slug = options.get("slug")
        if slug:
            courses = courses.filter(slug=slug)

        if not courses.exists():
            self.stdout.write(self.style.WARNING("No eligible published courses found."))
            return

        for course in courses:
            self.stdout.write(f"Firing {course.programme.webhook_line} webhook for: {course.title} ({course.slug})")
            notify_course_published(course)

        self.stdout.write(self.style.SUCCESS(
            f"Done — attempted {courses.count()} webhook(s). Check logs for any that failed to send "
            "(a failure is logged, not raised, and does not stop the rest)."
        ))
