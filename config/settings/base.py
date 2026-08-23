"""
Settings shared by every environment. dev.py and prod.py both start with
`from .base import *` and override what differs.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# In dev, values come from .env. In prod (Render), they come from real
# environment variables, so a missing .env file there is expected, not
# an error.
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Non-default admin URL path — see .env.example. Never leave this at
# the default "admin/" in a deployed environment.
ADMIN_URL_PATH = env("DJANGO_ADMIN_URL_PATH", default="admin/")

# --- Paystack (Phase 6) ---------------------------------------------
# See the payments addendum (kept alongside the build spec, not
# committed): this Paystack account is SHARED with Xpress Vet
# Marketplace. One webhook URL per account, already pointed at Xpress
# Vet's backend — Academy cannot use it. No webhook view exists in
# this codebase; payment status is determined by verify-on-return +
# reconciliation, never by being told. See apps/payments/gateway.py,
# services.py, and ARCHITECTURE.md.
PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY", default="")
PAYSTACK_PUBLIC_KEY = env("PAYSTACK_PUBLIC_KEY", default="")
# "shared_xpressvet" | "academy_own" — informational only for now,
# read by ops/support tooling later. Switching Paystack businesses is
# meant to be a config change, not a code change.
PAYSTACK_ACCOUNT_LABEL = env("PAYSTACK_ACCOUNT_LABEL", default="shared_xpressvet")
# Deliberately not wired to anything yet — no webhook view exists.
# Reserved so flipping it on later doesn't require a code change to
# this setting, only to config/urls.py adding the view.
PAYSTACK_WEBHOOK_ENABLED = env.bool("PAYSTACK_WEBHOOK_ENABLED", default=False)

# Used to build the mandatory per-transaction callback_url. Must be
# the scheme+host the learner will actually be redirected back to.
SITE_URL = env("SITE_URL", default="http://localhost:8000")

# --- Celery (Phase 7) -------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# Match TIME_ZONE below — the beat schedule in config/celery.py is
# written in WAT ("daily 09:00 WAT" per spec §5), and this is what
# makes crontab(hour=9) actually mean 9am Lagos time, not UTC.
CELERY_TIMEZONE = "Africa/Lagos"
CELERY_TASK_ALWAYS_EAGER = False  # dev.py flips this on — no worker/Redis needed locally

# --- Email / Resend (Phase 7) ------------------------------------------
RESEND_API_KEY = env("RESEND_API_KEY", default="")
# Sent-from address falls back to the Organization's own from_email
# (set per-org in admin) when not overridden here — see
# apps/engagement/services.py.
DEFAULT_FROM_EMAIL_FALLBACK = env("DEFAULT_FROM_EMAIL_FALLBACK", default="academy@xpressdigital.ng")
# A generous ceiling, not a target — see apps/engagement/services.py::send_email.
EMAIL_RATE_LIMIT_PER_MINUTE = env.int("EMAIL_RATE_LIMIT_PER_MINUTE", default=100)

# --- Interim SMTP fallback, before Resend is set up -----------------
# Supabase has no general-purpose transactional-email API for an app
# outside its own Auth flows (and this project deliberately doesn't
# use Supabase Auth — see Phase 1 notes), so it isn't a fit here.
# Django's own SMTP backend against a real mailbox is: set
# EMAIL_HOST_USER to a Gmail address and EMAIL_HOST_PASSWORD to a
# Gmail "App Password" (myaccount.google.com/apppasswords — needs
# 2-Step Verification on first) and send_email() in
# apps/engagement/services.py uses this path automatically whenever
# RESEND_API_KEY is blank but these are set. Leave both blank to fall
# back further to the log-only dev no-op.
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# --- Operations digest (Phase 11) ---------------------------------------
# Where the daily digest and interrupts actually land — deliberately
# NOT hardcoded to a person's address anywhere in source. Empty by
# default; apps.operations.services falls back to the first superuser's
# email at send time if this is unset, so the app still works out of
# the box, but the real address belongs in env/Render, not in git.
OPS_ALERT_EMAIL = env("OPS_ALERT_EMAIL", default="")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # Third-party — admin authoring UX only, no learner-facing footprint
    "adminsortable2",
    "django_ckeditor_5",
    # Local apps
    "apps.common",
    "apps.organizations",
    "apps.accounts",
    "apps.catalog",
    "apps.enrollment",
    "apps.assessment",
    "apps.certificates",
    "apps.operations",
    "apps.instructors",
    "apps.payments",
    "apps.engagement",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.payments.middleware.ReferralCaptureMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Nigerian audience throughout — WAT, not UTC, for anything a human reads
# (digest timing in Phase 11, "sent at" timestamps, etc.)
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# django-ckeditor-5 — admin-only rich text (lesson bodies, course
# descriptions). Basic toolbar; this is an authoring aid, not a design
# surface. Chosen over the older `django-ckeditor` package, which
# still bundles CKEditor 4 with unfixed security issues — see
# https://ckeditor.com/ckeditor-4-support/. No file-upload plugin
# wired yet (not needed for Phase 2's plain formatted-text use case);
# add CKEDITOR_5_FILE_STORAGE + the upload URL if lesson notes need
# embedded images later.
CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading", "|",
            "bold", "italic", "underline", "|",
            "bulletedList", "numberedList", "blockQuote", "|",
            "link", "|",
            "undo", "redo",
        ],
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/account/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"  # the public landing page, since Phase 8

# Structured logging to stdout — Render captures it from there.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
}
