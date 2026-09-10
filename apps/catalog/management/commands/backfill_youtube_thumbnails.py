"""Re-sets the custom thumbnail for every already-uploaded YouTube video,
using the local render already sitting in video/out/ (no Cloudinary
re-download needed, unlike the upload-time path in attach_to_youtube).

Why this exists: attach_to_youtube's own thumbnail step is
fire-and-forget -- a failure there (confirmed to happen at least once
live: "thumbnail upload failed (video is still live): 403") is logged
as a warning and never recorded anywhere, so there's no DB field to
query "which videos are missing a thumbnail." Re-running set_thumbnail
is safe and idempotent regardless: a video that already has the right
thumbnail just gets the same image re-applied, a no-op in substance.

Only fixes what CAN be fixed from here -- a channel without YouTube's
phone verification would still 403 on every one of these the same way
it would 403 at upload time; this can't work around that, only confirm
whether it's happening.

A small delay between calls (THUMBNAIL_PACE_SECONDS) is deliberate,
not incidental -- confirmed live that firing thumbnails.set in a tight
loop across ~25 videos hits a real 429 after the 3rd call. set_thumbnail
itself now also retries a 429 with backoff, but pacing calls up front
means most runs never need to."""
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.management.commands.attach_to_youtube import eligible_upload_kind, extract_thumbnail
from apps.catalog.models import Lesson
from apps.catalog.youtube_upload import set_thumbnail

VIDEO_OUT_DIR = Path(settings.BASE_DIR) / "video" / "out"
TEASER_DIR = VIDEO_OUT_DIR / "teasers"
THUMBNAIL_PACE_SECONDS = 1.5


class Command(BaseCommand):
    help = "Re-sets the YouTube thumbnail for every already-uploaded lesson, from the local render."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List what would be set, upload nothing.")

    def handle(self, *args, **options):
        if not (settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET and settings.YOUTUBE_REFRESH_TOKEN):
            raise CommandError("YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN aren't all set.")

        lessons = (
            Lesson.objects.exclude(youtube_video_id="")
            .select_related("module__course__programme")
            .order_by("pk")
        )
        if not lessons:
            self.stdout.write(self.style.WARNING("No lessons with a youtube_video_id set."))
            return

        ok, missing_local_file, failed = 0, [], []
        for lesson in lessons:
            course = lesson.module.course
            kind = eligible_upload_kind(course)
            is_teaser = kind == "teaser"

            if is_teaser:
                # Track subfolder under TEASER_DIR isn't derivable from the
                # Lesson/Course models (it's VideoScene.track, only known
                # at render time) -- glob for it instead.
                candidates = list(TEASER_DIR.glob(f"*/{lesson.slug}.mp4"))
            else:
                candidates = list(VIDEO_OUT_DIR.glob(f"*/{lesson.slug}/LessonVideo.mp4"))

            if not candidates:
                missing_local_file.append(lesson.slug)
                continue
            video_path = candidates[0]

            if options["dry_run"]:
                self.stdout.write(f"Would set thumbnail for {lesson.youtube_video_id} ({lesson.title}) from {video_path}")
                continue

            thumb_path = video_path.parent / f"{lesson.slug}-thumb.jpg"
            if not extract_thumbnail(video_path, thumb_path):
                failed.append((lesson.slug, "extract_thumbnail failed (ffmpeg/corrupt video)"))
                continue

            try:
                set_thumbnail(lesson.youtube_video_id, str(thumb_path))
                self.stdout.write(f"OK: {lesson.youtube_video_id} ({lesson.title})")
                ok += 1
            except Exception as e:
                failed.append((lesson.slug, str(e)))
                self.stdout.write(self.style.WARNING(f"FAILED: {lesson.youtube_video_id} ({lesson.title}): {e}"))
            finally:
                thumb_path.unlink(missing_ok=True)
                time.sleep(THUMBNAIL_PACE_SECONDS)

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"Done — {ok} thumbnail(s) set."))
        if missing_local_file:
            self.stdout.write(self.style.WARNING(
                f"No local render found (can't backfill without re-downloading from Cloudinary): "
                f"{', '.join(missing_local_file)}"
            ))
        if failed:
            self.stdout.write(self.style.ERROR(f"{len(failed)} real failure(s):"))
            for slug, err in failed:
                self.stdout.write(f"  {slug}: {err}")
