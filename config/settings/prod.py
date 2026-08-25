"""
Production settings, used on Render. Every required value comes from
the environment — see .env.example for the checklist.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# ALLOWED_HOSTS / CSRF_TRUSTED_ORIGINS come from base.py, sourced from
# env — deliberately no wildcard default here.
if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production.")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- Database ---------------------------------------------------------
# Supabase Postgres. See build spec §3: if DATABASE_URL points at the
# transaction-mode pooler (port 6543), server-side cursors must be
# disabled and connections must not be persisted by Django itself
# (pgbouncer does the pooling). Use the direct connection (port 5432)
# for `migrate` — see README for which URL to export when running
# migrations vs running the app.
DATABASES = {"default": env.db("DATABASE_URL")}

_using_transaction_pooler = ":6543" in env("DATABASE_URL")
if _using_transaction_pooler:
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    DATABASES["default"]["CONN_MAX_AGE"] = 0

# --- Email --------------------------------------------------------
# Real sending happens through apps.engagement.services.send_email(),
# which wraps the Resend HTTP API — nothing calls Resend directly.
# EMAIL_BACKEND here is Django's own mail plumbing, unused by that
# service, but left at a safe default in case anything falls back to
# django.core.mail directly during development of a new app.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# --- File storage (certificates, course covers) ------------------------
# Local disk storage (the base.py/dev.py default) doesn't work in prod:
# Django refuses to serve MEDIA_URL when DEBUG=False (by design — never
# re-enable that), and Render's free tier has no persistent disk anyway,
# so a saved file wouldn't survive the next redeploy even if it were
# served. Supabase already hosts the database — reusing its
# S3-compatible Storage API avoids a second third-party account.
#
# Only activates when AWS_STORAGE_BUCKET_NAME is set, so this file
# doesn't force the bucket to exist before the app can deploy at all —
# until it's set, prod silently keeps local storage (broken for the
# same reason as before, but not a new failure mode).
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
if AWS_STORAGE_BUCKET_NAME:
    # Mutates the dict base.py already built rather than reassigning
    # STORAGES wholesale — that would silently drop the "staticfiles"
    # key back to Django's built-in default (no manifest hashing, no
    # whitenoise compression) since noqa: F405 STORAGES here is the
    # same dict object base.py defined, imported via `from .base import *`.
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}  # noqa: F405
    AWS_ACCESS_KEY_ID = env("AWS_S3_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("AWS_S3_SECRET_ACCESS_KEY", default="")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
    # Supabase Storage buckets are marked public at the BUCKET level
    # (in its own dashboard), not via S3 object ACLs — Supabase's S3
    # gateway may not support ACL headers the way real AWS S3 does, so
    # deliberately not setting AWS_DEFAULT_ACL here.
    AWS_S3_ADDRESSING_STYLE = "path"  # Supabase's S3 gateway needs bucket-in-path, not subdomain
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False  # public bucket — plain URLs, no signed-query noise
