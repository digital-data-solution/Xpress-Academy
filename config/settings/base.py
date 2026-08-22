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


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
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
# No landing page at "/" until Phase 8 — send a logged-out user
# somewhere that actually resolves. Revisit once the public site exists.
LOGOUT_REDIRECT_URL = "/account/login/"

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
