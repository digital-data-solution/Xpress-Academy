"""Uploads lesson videos to the Xpress Digital Academy YouTube channel.

REAL business decision behind the branching logic below, not an
oversight: most courses on this platform are PAID (₦3,000+). Uploading
a full lecture video to a public YouTube channel would give away paid
content for free — the exact reasoning that made Vet Marketplace's
public distribution teasers-only earlier in this project. So:
  - Course.pricing_model == FREE  -> the FULL rendered lesson goes up.
    Nothing to protect; a full free lesson on YouTube is pure reach and
    funnels toward the paid catalog.
  - Anything else (PAID, PAY_WHAT_YOU_WANT, CERTIFICATE_PAID)  ->
    only the 30s TEASER goes up (video/out/teasers/<track>/<slug>.mp4,
    from video/scripts/render-lesson.mjs --composition=LessonVideoTeaser).
    A lesson with no teaser rendered yet is skipped, not silently
    substituted with the full paid video.

ONE-TIME SETUP for YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET /
YOUTUBE_REFRESH_TOKEN (do this once, then never again — the refresh
token doesn't expire from use):
  1. console.cloud.google.com -> new project -> enable "YouTube Data
     API v3".
  2. OAuth consent screen: External, add the channel owner's Google
     account as a test user (keeps it out of Google's review queue
     while testing).
  3. Credentials -> Create OAuth client ID -> Desktop app. Copy the
     Client ID and Client Secret.
  4. One-time authorization (run once, locally, never in this command):
     open this URL in a browser, signed into the SAME Google account
     that owns the YouTube channel:
       https://accounts.google.com/o/oauth2/v2/auth?client_id=<CLIENT_ID>&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/youtube.upload&access_type=offline&prompt=consent
     Approve it, copy the code Google shows you, then exchange it:
       curl -X POST https://oauth2.googleapis.com/token \\
         -d client_id=<CLIENT_ID> -d client_secret=<CLIENT_SECRET> \\
         -d code=<THE_CODE> -d grant_type=authorization_code \\
         -d redirect_uri=urn:ietf:wg:oauth:2.0:oob
     The response's "refresh_token" is YOUTUBE_REFRESH_TOKEN.

Real quota limit: 6 uploads/day on the default YouTube Data API quota
(10,000 units/day ÷ 1,600 per upload). --limit defaults to 6 for
exactly this reason — raise it only if the quota has actually been
increased in Google Cloud Console.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Course, Lesson
from apps.catalog.youtube_upload import YouTubeConfigError, YouTubeQuotaExceeded, upload_video


def eligible_upload_kind(course: Course) -> str | None:
    """Returns 'full', 'teaser', or None (not eligible at all) for a
    course — the one place the free/paid/staff-training decision from
    this file's module docstring actually lives, kept separate from
    the filesystem-globbing loop below so it's directly unit-testable.

    is_staff_training: real internal content (onboarding, admin
    dashboards, CRM training) that's FREE only in the sense of "not
    sold" — not public-facing. Caught in practice testing this command
    locally: without this check, "Admin: Xpress CRM Dashboard" would
    have gone straight to a public YouTube channel. Checked first, so
    it excludes a staff-training course regardless of pricing_model."""
    if course.is_staff_training:
        return None
    return "full" if course.pricing_model == Course.PricingModel.FREE else "teaser"

VIDEO_OUT_DIR = Path(settings.BASE_DIR) / "video" / "out"
TEASER_DIR = VIDEO_OUT_DIR / "teasers"
DEFAULT_DAILY_LIMIT = 6

ENROLL_URL_TEMPLATE = "{site_url}/courses/{course_slug}/"


YOUTUBE_TITLE_MAX = 100  # real YouTube hard limit


def _fit_title(lesson_title: str, course_title: str) -> str:
    """Builds 'Lesson — Course | Xpress Digital Academy', shortening
    piece by piece (never mid-word) until it's under YouTube's real
    100-char cap: drop the branding suffix first, then the course title,
    falling back to the lesson title alone (itself hard-truncated only
    as an absolute last resort — no lesson title in this catalog is
    remotely close to 100 chars on its own)."""
    full = f"{lesson_title} — {course_title} | Xpress Digital Academy"
    if len(full) <= YOUTUBE_TITLE_MAX:
        return full

    no_brand = f"{lesson_title} — {course_title}"
    if len(no_brand) <= YOUTUBE_TITLE_MAX:
        return no_brand

    if len(lesson_title) <= YOUTUBE_TITLE_MAX:
        return lesson_title

    return lesson_title[: YOUTUBE_TITLE_MAX - 1].rstrip() + "…"


def build_metadata(lesson: Lesson, course: Course, is_teaser: bool) -> dict:
    enroll_url = ENROLL_URL_TEMPLATE.format(site_url=settings.SITE_URL, course_slug=course.slug)
    title = _fit_title(lesson.title, course.title)

    if is_teaser:
        description = (
            f"A preview of \"{course.title}\" from Xpress Digital Academy.\n\n"
            f"{course.subtitle}\n\n"
            f"Enroll to watch the full course: {enroll_url}"
        )
    else:
        description = (
            f"{lesson.title}, from the free course \"{course.title}\" on Xpress Digital Academy.\n\n"
            f"{course.subtitle}\n\n"
            f"Take the full course free: {enroll_url}"
        )

    tags = ["Xpress Digital Academy", course.title, course.programme.title]
    return {"title": title, "description": description, "tags": tags}


class Command(BaseCommand):
    help = "Uploads lesson videos to YouTube — full video for FREE courses, teaser-only for paid ones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=DEFAULT_DAILY_LIMIT,
            help=f"Max uploads this run (default {DEFAULT_DAILY_LIMIT} — the real daily quota ceiling).",
        )
        parser.add_argument("--dry-run", action="store_true", help="List what would be uploaded, upload nothing.")

    def handle(self, *args, **options):
        if not (settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET and settings.YOUTUBE_REFRESH_TOKEN):
            raise CommandError(
                "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN aren't all set. "
                "See this command's own docstring for the one-time setup."
            )

        candidates = []  # (lesson, course, file_path, is_teaser)
        for full_mp4 in sorted(VIDEO_OUT_DIR.glob("*/*/LessonVideo.mp4")):
            slug = full_mp4.parent.name
            lesson = Lesson.objects.filter(slug=slug).select_related("module__course__programme").first()
            if not lesson or lesson.youtube_video_id:
                continue
            course = lesson.module.course
            if eligible_upload_kind(course) == "full":
                candidates.append((lesson, course, full_mp4, False))

        for teaser_mp4 in sorted(TEASER_DIR.glob("*/*.mp4")):
            slug = teaser_mp4.stem
            lesson = Lesson.objects.filter(slug=slug).select_related("module__course__programme").first()
            if not lesson or lesson.youtube_video_id:
                continue
            course = lesson.module.course
            if eligible_upload_kind(course) == "teaser":
                candidates.append((lesson, course, teaser_mp4, True))

        if not candidates:
            self.stdout.write(self.style.WARNING("Nothing new to upload (either none rendered, or all done)."))
            return

        limit = options["limit"]
        batch = candidates[:limit]
        self.stdout.write(f"{len(candidates)} eligible, uploading {len(batch)} (--limit={limit}).")

        uploaded = 0
        for lesson, course, file_path, is_teaser in batch:
            kind = "teaser" if is_teaser else "full video"
            metadata = build_metadata(lesson, course, is_teaser)

            if options["dry_run"]:
                self.stdout.write(f"Would upload ({kind}): {metadata['title']}")
                continue

            try:
                video_id = upload_video(
                    str(file_path),
                    title=metadata["title"],
                    description=metadata["description"],
                    tags=metadata["tags"],
                )
                lesson.youtube_video_id = video_id
                lesson.save(update_fields=["youtube_video_id"])
                uploaded += 1
                self.stdout.write(self.style.SUCCESS(
                    f"Uploaded ({kind}): {metadata['title']} -> https://youtu.be/{video_id}"
                ))
            except YouTubeQuotaExceeded:
                self.stdout.write(self.style.ERROR(
                    "Daily YouTube upload quota reached — stopping here. Re-run tomorrow to continue."
                ))
                break
            except YouTubeConfigError:
                raise
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FAILED for lesson {lesson.pk} ({file_path.name}): {e}"))

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"\nDone — {uploaded} video(s) uploaded this run."))
