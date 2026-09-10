"""Uploads lesson videos to the Xpress Digital Academy YouTube channel.

REAL business decision behind the branching logic below, not an
oversight: most courses on this platform are PAID (₦3,000+). Uploading
a full lecture video to a public YouTube channel would give away paid
content for free — the exact reasoning that made Vet Marketplace's
public distribution teasers-only earlier in this project. So:
  - Course.pricing_model == FREE  -> the FULL rendered lesson goes up
    (Lesson.generated_video_url, falling back to generated_video —
    see those fields' comments). Nothing to protect; a full free
    lesson on YouTube is pure reach and funnels toward the paid
    catalog.
  - Anything else (PAID, PAY_WHAT_YOU_WANT, CERTIFICATE_PAID)  ->
    only the 30s TEASER goes up (Lesson.generated_teaser_url). A
    lesson with no teaser uploaded to Cloudinary yet (see
    attach_generated_videos --teasers) is skipped, not silently
    substituted with the full paid video.

Reads Cloudinary URLs from the database and downloads each video to a
temp file before handing it to YouTube — NOT the local filesystem
(video/out/ never exists where this actually needs to run: GitHub
Actions' hosted runner). This is why attach_generated_videos --cloudinary
(and --teasers) has to run FIRST, from wherever the video was actually
rendered, before this command has anything to find.

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
     that owns the YouTube channel — note BOTH scopes, upload alone
     isn't enough for the playlist calls below:
       https://accounts.google.com/o/oauth2/v2/auth?client_id=<CLIENT_ID>&redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&scope=https://www.googleapis.com/auth/youtube%20https://www.googleapis.com/auth/youtube.upload&access_type=offline&prompt=consent
     Approve it, copy the code Google shows you, then exchange it:
       curl -X POST https://oauth2.googleapis.com/token \\
         -d client_id=<CLIENT_ID> -d client_secret=<CLIENT_SECRET> \\
         -d code=<THE_CODE> -d grant_type=authorization_code \\
         -d redirect_uri=urn:ietf:wg:oauth:2.0:oob
     The response's "refresh_token" is YOUTUBE_REFRESH_TOKEN.

Real quota limit: 6 uploads/day on the default YouTube Data API quota
(10,000 units/day ÷ 1,600 per upload). --limit defaults to 1, not 6 —
a deliberate content-strategy choice (a steady daily drip reads as an
active channel; a burst upload floods subscribers once and goes
quiet), not the quota ceiling itself. Raise it if you actually want
more than one upload in a single run.
"""
import tempfile
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Course, Lesson
from apps.catalog.youtube_upload import (
    YouTubeConfigError,
    YouTubeQuotaExceeded,
    add_video_to_playlist,
    create_playlist,
    set_thumbnail,
    upload_video,
)


def eligible_upload_kind(course: Course) -> str | None:
    """Returns 'full', 'teaser', or None (not eligible at all) for a
    course — the one place the free/paid/staff-training decision from
    this file's module docstring actually lives, kept separate from
    the candidate-gathering query below so it's directly unit-testable.

    is_staff_training: real internal content (onboarding, admin
    dashboards, CRM training) that's FREE only in the sense of "not
    sold" — not public-facing. Caught in practice testing this command
    locally: without this check, "Admin: Xpress CRM Dashboard" would
    have gone straight to a public YouTube channel. Checked first, so
    it excludes a staff-training course regardless of pricing_model."""
    if course.is_staff_training:
        return None
    return "full" if course.pricing_model == Course.PricingModel.FREE else "teaser"


DEFAULT_RUN_LIMIT = 1

ENROLL_URL_TEMPLATE = "{site_url}/courses/{course_slug}/"

# Every lesson opens on a real titleCard scene (see video/src/scenes/
# TitleCard.tsx) — its fade-in finishes well before this timestamp, so
# grabbing a frame here reliably captures the lesson title, course
# name, and track-themed colors cleanly, rather than YouTube's own
# auto-picked frame (which could land mid-caption on a content scene).
THUMBNAIL_TIMESTAMP = "00:00:01.2"


def extract_thumbnail(video_path: Path, out_path: Path) -> bool:
    """Grabs one frame from `video_path` at THUMBNAIL_TIMESTAMP and
    writes it to `out_path` as a JPEG, via ffmpeg (present on GitHub's
    hosted ubuntu-latest runners by default — no extra setup needed —
    and already a hard dependency of this pipeline locally, since
    video/src/captions/transcribe.ts resamples audio with it too).
    Returns False (not raises) on any failure — ffmpeg missing, a
    corrupt video file — since a missing thumbnail should never block
    the video upload itself."""
    import os
    import subprocess

    ffmpeg_bin = os.environ.get("FFMPEG_PATH", "ffmpeg")  # same env var convention as video/src/captions/transcribe.ts
    try:
        result = subprocess.run(
            [ffmpeg_bin, "-y", "-ss", THUMBNAIL_TIMESTAMP, "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", str(out_path)],
            capture_output=True, timeout=30,
        )
        return result.returncode == 0 and out_path.exists()
    except (OSError, subprocess.SubprocessError):
        return False


def download_to(url: str, dest: Path) -> None:
    """Streams `url` (a Cloudinary video URL) to `dest`. Raises
    requests.HTTPError on a real failure — caller's retry-per-lesson
    loop handles it the same as any other upload-step failure."""
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


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


def gather_candidates():
    """Real DB query, not a filesystem walk — see this file's module
    docstring for why. Returns a list of (lesson, course, video_url,
    is_teaser), ordered by pk so a run is deterministic (matters for
    --limit picking the "same" next batch across retries after a
    partial failure)."""
    candidates = []

    # Not pre-filtered at the DB level by generated_video_url/
    # generated_video — a FileField's "empty" state is null-or-blank,
    # not just blank, which makes a clean exclude() awkward for an "OR
    # either is set" check. The lesson counts here are in the
    # hundreds, not millions, so filtering in Python below (the `if
    # url` guard) is simpler and just as correct.
    full_lessons = (
        Lesson.objects.filter(youtube_video_id="")
        .select_related("module__course__programme")
        .order_by("pk")
    )
    for lesson in full_lessons:
        course = lesson.module.course
        if eligible_upload_kind(course) != "full":
            continue
        url = lesson.generated_video_url or (lesson.generated_video.url if lesson.generated_video else "")
        if url:
            candidates.append((lesson, course, url, False))

    teaser_lessons = (
        Lesson.objects.filter(youtube_video_id="")
        .exclude(generated_teaser_url="")
        .select_related("module__course__programme")
        .order_by("pk")
    )
    for lesson in teaser_lessons:
        course = lesson.module.course
        if eligible_upload_kind(course) != "teaser":
            continue
        candidates.append((lesson, course, lesson.generated_teaser_url, True))

    return candidates


class Command(BaseCommand):
    help = "Uploads lesson videos to YouTube — full video for FREE courses, teaser-only for paid ones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=DEFAULT_RUN_LIMIT,
            help=f"Max uploads this run (default {DEFAULT_RUN_LIMIT} — a deliberate daily-drip pace, "
                 "not the API's own 6/day quota ceiling).",
        )
        parser.add_argument("--dry-run", action="store_true", help="List what would be uploaded, upload nothing.")

    def handle(self, *args, **options):
        if not (settings.YOUTUBE_CLIENT_ID and settings.YOUTUBE_CLIENT_SECRET and settings.YOUTUBE_REFRESH_TOKEN):
            raise CommandError(
                "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN aren't all set. "
                "See this command's own docstring for the one-time setup."
            )

        # Same incident class documented in apps.catalog.webhooks and
        # resend_vet_webhooks: a local one-off run against
        # config.settings.prod (DATABASE_URL + the YOUTUBE_* secrets set,
        # but SITE_URL left unset) silently inherits SITE_URL from this
        # project's local .env ("http://localhost:8000") instead of
        # Render's real value. Unlike those two, this command had no
        # guard at all -- it actually happened here: 6 real, public
        # YouTube uploads (2026-09-10) shipped with a dead localhost
        # enroll link baked into the description, permanently (YouTube
        # descriptions are still fixable after the fact via videos.update,
        # see fix_youtube_localhost_links, but the upload itself already
        # went out). Gated on SETTINGS_MODULE, not DEBUG, for the same
        # reason as webhooks.py: Django's test runner forces DEBUG=False
        # for every test regardless of settings module.
        is_localhost_url = "localhost" in settings.SITE_URL or "127.0.0.1" in settings.SITE_URL
        is_prod_settings = settings.SETTINGS_MODULE == "config.settings.prod"
        if is_localhost_url and is_prod_settings:
            raise CommandError(
                f"SITE_URL is {settings.SITE_URL!r} under config.settings.prod -- every video's "
                "description would ship a dead localhost enroll link to real, public YouTube "
                "uploads. Set SITE_URL explicitly for this process, the same way DATABASE_URL is:\n"
                '  $env:SITE_URL = "https://xpress-academy-web.onrender.com"'
            )

        candidates = gather_candidates()
        if not candidates:
            self.stdout.write(self.style.WARNING("Nothing new to upload (either none rendered, or all done)."))
            return

        limit = options["limit"]
        batch = candidates[:limit]
        self.stdout.write(f"{len(candidates)} eligible, uploading {len(batch)} (--limit={limit}).")

        uploaded = 0
        for lesson, course, video_url, is_teaser in batch:
            kind = "teaser" if is_teaser else "full video"
            metadata = build_metadata(lesson, course, is_teaser)

            if options["dry_run"]:
                self.stdout.write(f"Would upload ({kind}): {metadata['title']}")
                continue

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                video_path = tmp_path / f"{lesson.slug}.mp4"
                try:
                    download_to(video_url, video_path)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"FAILED to download for lesson {lesson.pk}: {e}"))
                    continue

                try:
                    video_id = upload_video(
                        str(video_path),
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

                    # Real title-card frame instead of YouTube's own
                    # auto-picked one — see extract_thumbnail's comment.
                    # Non-fatal on any failure: a channel without phone
                    # verification (a real YouTube requirement, not
                    # something this code controls) gets a 403 here, and
                    # the video itself has already uploaded successfully.
                    thumb_path = tmp_path / f"{lesson.slug}-thumb.jpg"
                    if extract_thumbnail(video_path, thumb_path):
                        try:
                            set_thumbnail(video_id, str(thumb_path))
                            self.stdout.write("  custom thumbnail set")
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(
                                f"  thumbnail upload failed (video is still live): {e}"
                            ))

                    # One playlist per Course — created the first time any
                    # of its lessons uploads, every later lesson (including
                    # ones added to the catalog after) just appends to the
                    # same playlist. Non-fatal on failure: the video is
                    # already live either way.
                    try:
                        if not course.youtube_playlist_id:
                            course.youtube_playlist_id = create_playlist(
                                title=f"{course.title} | Xpress Digital Academy",
                                description=course.subtitle or course.title,
                            )
                            course.save(update_fields=["youtube_playlist_id"])
                            self.stdout.write(f"  created playlist for {course.title}")
                        add_video_to_playlist(course.youtube_playlist_id, video_id)
                        self.stdout.write("  added to playlist")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"  playlist step failed (video is still live): {e}"))
                except YouTubeQuotaExceeded:
                    self.stdout.write(self.style.ERROR(
                        "Hit a real daily YouTube limit (API quota or the separate per-day upload-count "
                        "cap — see YouTubeQuotaExceeded's own docstring) — stopping here. Re-run tomorrow "
                        "to continue."
                    ))
                    break
                except YouTubeConfigError:
                    raise
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"FAILED for lesson {lesson.pk}: {e}"))

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(f"\nDone — {uploaded} video(s) uploaded this run."))
