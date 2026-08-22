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
