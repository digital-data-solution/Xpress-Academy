"""Direct Cloudinary REST API call for uploading a generated lesson
video — no cloudinary SDK, same house pattern as apps.payments.gateway
and apps.engagement.gateway (a thin client over `requests`, not a
third-party SDK for a single endpoint).

Cloudinary's authenticated (signed) upload: sort the params you're
sending (besides file/api_key/signature itself) alphabetically, join as
`key=value&key2=value2`, SHA-1 hash that string with the API secret
appended, and send api_key + timestamp + signature alongside the file.
See https://cloudinary.com/documentation/authentication_signatures
"""
import hashlib
import time

import requests
from django.conf import settings


class CloudinaryConfigError(Exception):
    """CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET aren't all set."""


def _signature(params: dict, api_secret: str) -> str:
    to_sign = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.sha1(f"{to_sign}{api_secret}".encode()).hexdigest()


def upload_video(file_path: str, public_id: str, folder: str = "lessons/generated-video") -> str:
    """Uploads the file at `file_path` to Cloudinary under `public_id`
    (e.g. a lesson's slug) and returns the real `secure_url`. `folder`
    defaults to the full-lesson path; attach_generated_videos --teasers
    passes "lessons/generated-teaser" to keep the two kinds visually
    separated in the Cloudinary dashboard. Raises CloudinaryConfigError
    if the three settings aren't all set, or requests.RequestException
    (uncaught — callers handle/retry, same as the S3 upload path in
    attach_generated_videos) on a real HTTP failure."""
    cloud_name = settings.CLOUDINARY_CLOUD_NAME
    api_key = settings.CLOUDINARY_API_KEY
    api_secret = settings.CLOUDINARY_API_SECRET
    if not (cloud_name and api_key and api_secret):
        raise CloudinaryConfigError(
            "CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET aren't all set."
        )

    timestamp = int(time.time())
    params_to_sign = {"timestamp": timestamp, "public_id": public_id, "folder": folder}
    signature = _signature(params_to_sign, api_secret)

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"https://api.cloudinary.com/v1_1/{cloud_name}/video/upload",
            data={
                "api_key": api_key,
                "timestamp": timestamp,
                "signature": signature,
                "public_id": public_id,
                "folder": folder,
            },
            files={"file": f},
            timeout=120,  # video uploads are large; the default timeout is too short
        )
    resp.raise_for_status()
    return resp.json()["secure_url"]
