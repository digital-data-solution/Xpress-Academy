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
import uuid

import requests
from django.conf import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeConfigError(Exception):
    """YOUTUBE_CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN aren't all set."""


class YouTubeQuotaExceeded(Exception):
    """The daily upload quota (a real Google-side limit, not this
    codebase's own invention) has been used up — stop the run, don't
    retry."""


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

    if resp.status_code == 403 and "quotaExceeded" in resp.text:
        raise YouTubeQuotaExceeded(resp.text)
    resp.raise_for_status()
    return resp.json()["id"]
