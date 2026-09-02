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
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
# dev.py flips this on unconditionally — no worker/Redis needed locally.
# In prod, this stays False (real async via worker+beat+Redis) unless
# explicitly overridden — a deliberate escape hatch for running the web
# service alone, free-tier, before there's revenue to justify paying for
# a worker+beat+Redis. Flip back to False (or unset) once those are
# provisioned for real background processing.

# --- Email / Resend (Phase 7) ------------------------------------------
RESEND_API_KEY = env("RESEND_API_KEY", default="")
# Sent-from address falls back to the Organization's own from_email
# (set per-org in admin) when not overridden here — see
# apps/engagement/services.py.
DEFAULT_FROM_EMAIL_FALLBACK = env(
    "DEFAULT_FROM_EMAIL_FALLBACK",
    default="Xpress Digital Academy <academy@xpressdigitalanddatasolutions.online>",
)
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
# Some hosts block/filter outbound SMTP on 587 (STARTTLS) but allow
# 465 (implicit SSL) or vice versa — seen in practice on Render's free
# tier. Set EMAIL_PORT=465 and EMAIL_USE_SSL=True (leaves
# EMAIL_USE_TLS as whatever, only one of the two is actually passed
# to the backend below) to try the other path without a code change.
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

# --- Operations digest (Phase 11) ---------------------------------------
# Where the daily digest and interrupts actually land — deliberately
# NOT hardcoded to a person's address anywhere in source. Empty by
# default; apps.operations.services falls back to the first superuser's
# email at send time if this is unset, so the app still works out of
# the box, but the real address belongs in env/Render, not in git.
OPS_ALERT_EMAIL = env("OPS_ALERT_EMAIL", default="")
# Authorizes the free-tier scheduled-task workaround (see
# apps.engagement.views.run_scheduled_tasks) — required (non-empty)
# to actually run anything; a blank value refuses every request
# rather than accepting an "empty token" as valid.
CRON_SECRET = env("CRON_SECRET", default="")

# --- Course-publish webhooks ---------------------------------------------
# Outbound-only notifications fired when a Course flips draft→published
# (see apps.catalog.webhooks.notify_course_published, called from
# Course.save()). Deliberately does NOT email anyone itself — it just
# tells an external system a course went live, so a human decides what
# to send. Blank by default (no URL/secret in source, same discipline
# as OPS_ALERT_EMAIL/CRON_SECRET above) — a blank URL means that
# destination is simply skipped, not sent unauthenticated. Two
# independent destinations, one per Programme.WebhookLine — which one
# (if any) fires for a given course is chosen by that course's
# Programme, not by these settings.
COURSE_PUBLISH_WEBHOOK_URL = env("COURSE_PUBLISH_WEBHOOK_URL", default="")
COURSE_PUBLISH_WEBHOOK_SECRET = env("COURSE_PUBLISH_WEBHOOK_SECRET", default="")
VET_COURSE_PUBLISH_WEBHOOK_URL = env("VET_COURSE_PUBLISH_WEBHOOK_URL", default="")
VET_COURSE_PUBLISH_WEBHOOK_SECRET = env("VET_COURSE_PUBLISH_WEBHOOK_SECRET", default="")

# --- Staff-training completion webhook ------------------------------------
# Outbound-only, same discipline as the course-publish webhooks above:
# fired once, the moment a staff member (is_staff=True) completes a
# Course with is_staff_training=True (see
# apps.enrollment.webhooks.notify_staff_training_completed, called from
# apps.enrollment.services._mark_enrollment_completed_if_ready). Blank
# by default — that destination (the HR/CRM system, currently a
# separate Claude Code session's app) doesn't exist yet as a concrete
# endpoint; this fires as a genuine no-op until it's configured.
STAFF_TRAINING_WEBHOOK_URL = env("STAFF_TRAINING_WEBHOOK_URL", default="")
STAFF_TRAINING_WEBHOOK_SECRET = env("STAFF_TRAINING_WEBHOOK_SECRET", default="")

# --- Call-assignment read-only integration --------------------------------
# INBOUND, unlike every other integration setting above — authorizes
# apps.enrollment.views.call_candidates, a small read-only endpoint the
# Xpress Digital & Data Solutions "Call Assignment" system can query to
# pull real Academy learner/enrollment segments (filtered by course/
# programme/status) instead of Sam pasting names in by hand. Blank by
# default — refuses every request rather than accepting an empty token
# as valid, same discipline as CRON_SECRET/the webhook secrets above.
# Read-only by construction (GET, no state changes); returns contact
# info (name, email, phone) because the whole point is letting Sam's
# own staff actually call these people — same trust level as Sam's own
# admin access, not an instructor-facing view (contrast the deliberate
# email/phone redaction in apps.instructors' learner-privacy rule,
# which is about an external party, not Sam's own internal ops tool).
CALL_ASSIGNMENT_API_SECRET = env("CALL_ASSIGNMENT_API_SECRET", default="")

# Same shape as CALL_ASSIGNMENT_API_SECRET above, for
# apps.operations.views.company_stats -- a separate, aggregate-only
# (no PII at all) endpoint feeding the same "Company Overview"
# dashboard's revenue side. Kept as its own secret, not reused, so
# either integration can be rotated/revoked independently.
COMPANY_STATS_API_SECRET = env("COMPANY_STATS_API_SECRET", default="")


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
    # Real TOTP two-factor auth — opt-in per account (see
    # apps.accounts.views.twofactor_setup), enforced at login only once
    # a user has actually confirmed a device, never a surprise lockout.
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",  # backup/recovery codes
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
    "apps.support",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",  # after auth — sets request.user.is_verified()
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

OTP_TOTP_ISSUER = "Xpress Digital Academy"

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
# Django 5.1 fully removed the old standalone DEFAULT_FILE_STORAGE /
# STATICFILES_STORAGE settings in favour of this single STORAGES
# dict — setting the old-style names is silently ignored (no error,
# no warning, just quietly does nothing), which is exactly what
# happened here: prod.py set DEFAULT_FILE_STORAGE to the S3 backend
# and it was never actually used, no matter how many times the app
# redeployed with correct env vars. config/settings/prod.py mutates
# STORAGES["default"] directly rather than redefining this whole
# dict, so it only overrides the file-storage backend and leaves
# "staticfiles" (whitenoise) alone.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
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
