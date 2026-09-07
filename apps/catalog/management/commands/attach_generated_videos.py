import time
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from apps.catalog.cloudinary_upload import CloudinaryConfigError, upload_video
from apps.catalog.models import Lesson

MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5

# The video/ pipeline writes finished renders to
# video/out/<track>/<lesson-slug>/LessonVideo.mp4 (see
# scripts/render-lesson.mjs's default output path). This command walks
# that tree and uploads each one to the matching Lesson — either through
# Django's own storage (S3 in prod, the default) or straight to
# Cloudinary with --cloudinary, writing generated_video_url instead.
# See Lesson.generated_video_url's comment for why there are two paths:
# Supabase's free tier is only 1GB, shared with certificates.
VIDEO_OUT_DIR = Path(settings.BASE_DIR) / "video" / "out"


class Command(BaseCommand):
    help = (
        "Uploads finished renders from video/out/<track>/<slug>/LessonVideo.mp4 to the matching "
        "Lesson — Django storage (generated_video) by default, or --cloudinary for "
        "generated_video_url. Run against prod the same way as any other prod-touching command "
        "here: DJANGO_SETTINGS_MODULE=config.settings.prod + DATABASE_URL (+ the real AWS_S3_* or "
        "CLOUDINARY_* vars), all pasted into your OWN terminal."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List what would be uploaded, upload nothing.")
        parser.add_argument(
            "--cloudinary", action="store_true",
            help="Upload to Cloudinary (generated_video_url) instead of Django/S3 storage (generated_video).",
        )

    def handle(self, *args, **options):
        if not VIDEO_OUT_DIR.exists():
            raise CommandError(f"{VIDEO_OUT_DIR} doesn't exist — nothing rendered yet?")

        use_cloudinary = options["cloudinary"]
        if use_cloudinary and not (settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET):
            raise CommandError(
                "--cloudinary needs CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET set."
            )

        found = sorted(VIDEO_OUT_DIR.glob("*/*/LessonVideo.mp4"))
        if not found:
            self.stdout.write(self.style.WARNING(f"No LessonVideo.mp4 files under {VIDEO_OUT_DIR}."))
            return

        uploaded, not_found, skipped, failed = 0, [], [], []
        for mp4_path in found:
            slug = mp4_path.parent.name
            lesson = Lesson.objects.filter(slug=slug).first()
            if not lesson:
                not_found.append(slug)
                continue

            # Safe to re-run after a partial failure (e.g. a network/SSL
            # hiccup mid-upload — that never reaches this point since
            # neither path below sets its field until the upload actually
            # succeeds) — already-uploaded lessons are skipped rather than
            # re-uploaded. Checks BOTH fields regardless of which mode
            # this run is in, so a lesson already on Cloudinary doesn't
            # also get pushed to S3 (or vice versa) by a later run.
            if lesson.generated_video_url or lesson.generated_video:
                skipped.append(slug)
                continue

            size_mb = mp4_path.stat().st_size / (1024 * 1024)
            if options["dry_run"]:
                dest = "Cloudinary" if use_cloudinary else "S3"
                self.stdout.write(f"Would upload to {dest}: {mp4_path} ({size_mb:.1f} MB) -> lesson {lesson.pk} ({lesson.title})")
                continue

            # Real network flakiness hit this in practice — an S3 SSL error
            # on one run, a dropped Postgres connection on the next.
            # close_old_connections() forces a fresh DB connection on
            # retry rather than reusing one Django already knows is dead.
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    if use_cloudinary:
                        url = upload_video(str(mp4_path), public_id=slug)
                        lesson.generated_video_url = url
                        lesson.save(update_fields=["generated_video_url"])
                    else:
                        with open(mp4_path, "rb") as f:
                            lesson.generated_video.save(f"{slug}.mp4", File(f), save=True)
                    uploaded += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"Uploaded {mp4_path.name} ({size_mb:.1f} MB) -> lesson {lesson.pk} ({lesson.title})"
                    ))
                    break
                except CloudinaryConfigError:
                    raise  # a real config problem, not a transient one — don't retry, don't hide it
                except Exception as e:
                    close_old_connections()
                    if attempt == MAX_ATTEMPTS:
                        self.stdout.write(self.style.ERROR(
                            f"FAILED (after {MAX_ATTEMPTS} attempts) for lesson {lesson.pk} ({slug}): "
                            f"{e.__class__.__name__}: {e}"
                        ))
                        failed.append(slug)
                    else:
                        self.stdout.write(self.style.WARNING(
                            f"  attempt {attempt}/{MAX_ATTEMPTS} failed ({e.__class__.__name__}) — retrying..."
                        ))
                        time.sleep(RETRY_DELAY_SECONDS)

        if not_found:
            self.stdout.write(self.style.WARNING(f"\nNo matching Lesson.slug for: {', '.join(not_found)}"))
        if skipped and not options["dry_run"]:
            self.stdout.write(f"Skipped {len(skipped)} already-uploaded lesson(s).")
        if failed:
            self.stdout.write(self.style.ERROR(f"\n{len(failed)} lesson(s) failed all {MAX_ATTEMPTS} attempts: {', '.join(failed)}"))
            self.stdout.write("Re-run this command to retry just those — everything else is already saved.")

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"\nDone — {uploaded} video(s) uploaded."))
