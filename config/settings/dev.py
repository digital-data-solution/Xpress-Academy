"""
Local development settings. `manage.py` defaults here via
DJANGO_SETTINGS_MODULE in manage.py — see that file.
"""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, env

DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = ["*"]

# Database: defaults to SQLite so `manage.py migrate` works with zero
# setup. Set DATABASE_URL in .env to point at local Postgres instead
# (docker-compose.yml in the repo root brings one up on 5432) — do
# this before Phase 4+, since JSONField/array behaviour and the
# pgbouncer pooling notes in the build spec (§3) only show up against
# real Postgres, not SQLite.
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Emails print to the console instead of sending — no Resend calls
# from a dev machine.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:8000", "http://127.0.0.1:8000"],
)
