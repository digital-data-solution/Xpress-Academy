"""One-off repair for a real incident (2026-09-10): a local run of
attach_to_youtube against config.settings.prod had DATABASE_URL and the
YOUTUBE_* secrets set, but not SITE_URL — which silently fell back to
this project's local .env value (SITE_URL=http://localhost:8000).
attach_to_youtube had no guard against that (unlike apps.catalog.webhooks
and resend_vet_webhooks, which both already carry this exact check —
see their comments for the earlier incident this one repeats). Result:
6 real, public YouTube uploads shipped with a dead
"Enroll to watch the full course: http://localhost:8000/courses/..."
link baked into their description. attach_to_youtube now refuses to run
under this exact condition, so this can't happen again going forward —
this command only repairs the videos that already went out before that
guard existed.

Rewrites every already-uploaded lesson's YouTube title+description via
videos.update, using the CURRENT (correct) settings.SITE_URL — safe to
run on lessons that were already correct (GitHub Actions' own runs
always had SITE_URL set properly), since it recomputes and reapplies
the same build_metadata() every other upload path uses; a no-op in
substance for those, just a wasted (cheap, 50-unit) API call. Run this
the same way as any other prod-touching one-off here: DJANGO_SETTINGS_MODULE
=config.settings.prod + DATABASE_URL + the YOUTUBE_* secrets, all set
explicitly in your own terminal — AND a real, non-localhost SITE_URL,
or this refuses for the same reason attach_to_youtube does."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.management.commands.attach_to_youtube import build_metadata, eligible_upload_kind
from apps.catalog.models import Lesson
from apps.catalog.youtube_upload import update_video_description


class Command(BaseCommand):
    help = "Repairs YouTube video descriptions that shipped with a dead localhost enroll link."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List what would change, update nothing.")

    def handle(self, *args, **options):
        is_localhost_url = "localhost" in settings.SITE_URL or "127.0.0.1" in settings.SITE_URL
        if is_localhost_url:
            raise CommandError(
                f"SITE_URL is {settings.SITE_URL!r} -- refusing to 'fix' every video's enroll link "
                "to point at localhost. Set the real SITE_URL first:\n"
                '  $env:SITE_URL = "https://xpress-academy-web.onrender.com"'
            )

        lessons = (
            Lesson.objects.exclude(youtube_video_id="")
            .select_related("module__course__programme")
            .order_by("pk")
        )
        if not lessons:
            self.stdout.write(self.style.WARNING("No lessons with a youtube_video_id set — nothing to fix."))
            return

        fixed, skipped = 0, []
        for lesson in lessons:
            course = lesson.module.course
            kind = eligible_upload_kind(course)
            if kind is None:
                # is_staff_training or otherwise no longer eligible -- was
                # uploaded under different rules at the time; leave alone
                # rather than guess which description shape it should have.
                skipped.append(lesson.slug)
                continue

            metadata = build_metadata(lesson, course, is_teaser=(kind == "teaser"))

            if options["dry_run"]:
                self.stdout.write(f"Would update {lesson.youtube_video_id} ({lesson.title}): {metadata['description'][-80:]}")
                continue

            update_video_description(lesson.youtube_video_id, metadata["title"], metadata["description"])
            self.stdout.write(f"Updated {lesson.youtube_video_id} ({lesson.title})")
            fixed += 1

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Done — {fixed} video(s) updated."))
        if skipped:
            self.stdout.write(self.style.WARNING(f"Skipped (no longer upload-eligible): {', '.join(skipped)}"))
