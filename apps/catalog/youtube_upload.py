"""Direct YouTube Data API v3 upload — no google-api-python-client SDK,
same house pattern as apps.payments.gateway and apps.catalog.
cloudinary_upload (a thin `requests` client over one endpoint, not a
full SDK for a single use case).

Auth: OAuth2 refresh-token flow, NOT an API key — the YouTube Data API
requires a real Google account authorization (the channel owner grants
upload permission once; after that, YOUTUBE_REFRESH_TOKEN mints fresh
access tokens indefinitely without any further human interaction). See
attach_to_youtube's own docstring for the one-time setup that produces
that refresh token.

Real quota constraint, not hypothetical: YouTube Data API's default
daily quota is 10,000 units, and a single video insert costs 1,600 —
so about 6 uploads/day on the default quota, hard reset at midnight
Pacific time. attach_to_youtube respects a --limit for exactly this
reason; it does not try to upload everything in one run.
"""
import json
import mimetypes
import time
import uuid

import requests
from django.conf import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
PLAYLISTS_URL = "https://www.googleapis.com/youtube/v3/playlists"
PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


class YouTubeConfigError(Exception):
    """YOUTUBE_CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN aren't all set."""


class YouTubeQuotaExceeded(Exception):
    """Either of two real, distinct Google-side daily limits, not this
    codebase's own invention -- both mean the same thing to a caller
    (stop the run, don't retry, come back tomorrow), so both raise this
    one exception:
    - 403 quotaExceeded: the 10,000-unit API quota itself.
    - 400 uploadLimitExceeded (confirmed live, 2026-09-10, via a batch
      of 6 real 400s whose body — only visible after upload_video
      started including it — read "The user has exceeded the number of
      videos they may upload", domain youtube.video): a SEPARATE cap on
      the raw count of videos uploaded per day, hit that day after ~23
      real uploads across several runs. Nothing here can raise the
      limit; the only real fix is spacing uploads out over more days."""


def _access_token() -> str:
    client_id = settings.YOUTUBE_CLIENT_ID
    client_secret = settings.YOUTUBE_CLIENT_SECRET
    refresh_token = settings.YOUTUBE_REFRESH_TOKEN
    if not (client_id and client_secret and refresh_token):
        raise YouTubeConfigError(
            "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN aren't all set."
        )

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _build_multipart_related(metadata: dict, video_bytes: bytes, content_type: str, boundary: str) -> bytes:
    """Builds the raw multipart/related body YouTube's `uploadType=multipart`
    expects: one application/json part (the metadata) followed by one
    binary part (the video), joined by the same boundary string used in
    the Content-Type header. Built by hand rather than via `requests`'
    own multipart support, which targets multipart/form-data (file
    uploads from an HTML form) — a different, incompatible wire format
    from multipart/related."""
    parts = [
        f"--{boundary}\r\n".encode(),
        b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
        json.dumps(metadata).encode("utf-8"),
        f"\r\n--{boundary}\r\n".encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        video_bytes,
        f"\r\n--{boundary}--".encode(),
    ]
    return b"".join(parts)


def upload_video(
    file_path: str,
    *,
    title: str,
    description: str,
    tags: list[str],
    privacy_status: str = "public",
) -> str:
    """Uploads the file at `file_path`, returns the real YouTube video ID.

    Raises YouTubeConfigError if credentials aren't set, YouTubeQuotaExceeded
    on a real quotaExceeded response from Google (caller should stop the
    whole run, not retry this one video), or requests.HTTPError on any
    other real failure."""
    access_token = _access_token()

    metadata = {
        "snippet": {
            "title": title[:100],  # YouTube's real hard limit
            "description": description[:5000],  # YouTube's real hard limit
            "tags": tags,
            "categoryId": "27",  # Education — real YouTube category ID
        },
        "status": {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False},
    }

    content_type = mimetypes.guess_type(file_path)[0] or "video/mp4"
    with open(file_path, "rb") as f:
        video_bytes = f.read()

    boundary = uuid.uuid4().hex
    body = _build_multipart_related(metadata, video_bytes, content_type, boundary)

    resp = requests.post(
        f"{UPLOAD_URL}?uploadType=multipart&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        data=body,
        timeout=300,  # a multi-MB video upload over a home connection needs real headroom
    )

    # requests.HTTPError's default str() is just "400 Client Error: Bad
    # Request for url: ..." -- the actual reason Google gives lives in
    # the response BODY, which raise_for_status() never surfaces.
    # Confirmed live (2026-09-10): a real batch of 400s gave zero
    # diagnostic value until a raw call captured resp.text directly.
    # Raising with the body included here means the next real failure
    # is diagnosable from the caller's own error message, not another
    # ad-hoc diagnostic script.
    if (resp.status_code == 403 and "quotaExceeded" in resp.text) or (
        resp.status_code == 400 and "uploadLimitExceeded" in resp.text
    ):
        raise YouTubeQuotaExceeded(resp.text)
    if not resp.ok:
        raise requests.HTTPError(f"{resp.status_code} {resp.reason} for {file_path}: {resp.text[:1000]}", response=resp)
    return resp.json()["id"]


def update_video_description(video_id: str, title: str, description: str) -> None:
    """Rewrites an already-uploaded video's title/description via
    videos.update. YouTube's videos.update replaces the entire `snippet`
    part it's given -- it is NOT a partial patch -- so this fetches the
    current snippet first (to preserve tags/categoryId untouched) and
    only overwrites title/description, rather than reconstructing a
    snippet from scratch and risking silently dropping a field a caller
    didn't think to pass. Built specifically to repair the localhost-
    enroll-link incident (see attach_to_youtube's SITE_URL guard and
    fix_youtube_localhost_links) but generically reusable for any future
    metadata correction on an already-public video."""
    access_token = _access_token()
    headers = {"Authorization": f"Bearer {access_token}"}

    get_resp = requests.get(
        VIDEOS_URL, params={"part": "snippet", "id": video_id}, headers=headers, timeout=30,
    )
    get_resp.raise_for_status()
    items = get_resp.json().get("items", [])
    if not items:
        raise ValueError(f"No YouTube video found for id {video_id!r}")

    snippet = items[0]["snippet"]
    snippet["title"] = title[:100]
    snippet["description"] = description[:5000]

    put_resp = requests.put(
        f"{VIDEOS_URL}?part=snippet",
        headers={**headers, "Content-Type": "application/json"},
        json={"id": video_id, "snippet": snippet},
        timeout=30,
    )
    put_resp.raise_for_status()


THUMBNAIL_SET_URL = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"


THUMBNAIL_MAX_RETRIES = 5


class YouTubeThumbnailRateLimited(Exception):
    """The real, distinct error Google returns for this (confirmed live,
    2026-09-10, via a raw diagnostic call that captured the actual JSON
    body instead of just the HTTP status): domain "youtube.thumbnail",
    reason "uploadRateLimitExceeded", message "The user has uploaded too
    many thumbnails recently." This is a SEPARATE, longer sliding-window
    limit from both the 10,000-unit daily quota (reason would be
    "quotaExceeded") and an ordinary short burst 429 -- no published
    reset window, but empirically longer than seconds: a 5-attempt
    exponential backoff (up to ~31s total) did NOT clear it. Retrying
    per-video here would just keep re-triggering it on every remaining
    video in a batch; callers should catch this and stop the whole run,
    not continue to the next video."""


def set_thumbnail(video_id: str, image_path: str) -> None:
    """Uploads a custom thumbnail for an already-uploaded video.

    Real constraint this code CAN'T work around: YouTube only allows
    custom thumbnails on channels that have completed phone verification
    (YouTube Studio -> Settings -> Channel -> Feature eligibility).
    Without it, this raises requests.HTTPError with a 403 — caller
    (attach_to_youtube / backfill_youtube_thumbnails) treats that as
    non-fatal: the video itself already uploaded fine, a missing custom
    thumbnail just means YouTube's own auto-picked frame is used instead.

    Real constraint this code CAN partially work around: an ordinary
    short-burst 429 (no specific reason, or a reason other than
    uploadRateLimitExceeded) gets exponential backoff (1s, 2s, 4s, 8s,
    16s) since that class of 429 does clear within seconds. A 429 that
    IS specifically uploadRateLimitExceeded raises YouTubeThumbnailRateLimited
    immediately instead of burning through the retry budget on a limit
    backoff can't clear in time."""
    access_token = _access_token()
    content_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    for attempt in range(THUMBNAIL_MAX_RETRIES):
        resp = requests.post(
            f"{THUMBNAIL_SET_URL}?videoId={video_id}",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": content_type},
            data=image_bytes,
            timeout=60,
        )
        if resp.status_code == 429:
            reason = None
            try:
                reason = resp.json()["error"]["errors"][0]["reason"]
            except (ValueError, KeyError, IndexError):
                pass
            if reason == "uploadRateLimitExceeded":
                raise YouTubeThumbnailRateLimited(resp.text)
            if attempt < THUMBNAIL_MAX_RETRIES - 1:
                time.sleep(2**attempt)
                continue
        resp.raise_for_status()
        return


def create_playlist(title: str, description: str) -> str:
    """Creates a new (public) playlist, returns its real YouTube
    playlist ID. One playlist per Course (see Course.youtube_playlist_id)
    — called once, the first time any lesson from that course uploads."""
    access_token = _access_token()
    resp = requests.post(
        f"{PLAYLISTS_URL}?part=snippet,status",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={
            "snippet": {"title": title[:150], "description": description[:5000]},  # real YouTube limits
            "status": {"privacyStatus": "public"},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def add_video_to_playlist(playlist_id: str, video_id: str) -> None:
    """Appends `video_id` to the end of `playlist_id` — called after
    every successful video upload for a course that already has (or
    just got) a playlist."""
    access_token = _access_token()
    resp = requests.post(
        f"{PLAYLIST_ITEMS_URL}?part=snippet",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
        timeout=30,
    )
    resp.raise_for_status()
