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
            # SQLite has no real row-level locking — select_for_update()
            # (used in apps.payments.services.grant_access) is a no-op
            # here and true concurrent writers instead contend for the
            # whole-database file lock. The default ~5s busy timeout is
            # too short for a burst of concurrent requests (surfaced by
            # apps/payments/tests.py's concurrency test) and raises
            # "database is locked" where Postgres would just serialize
            # the transactions and wait. Not a production concern —
            # Postgres (prod.py) has real row locking — but worth a
            # generous timeout here so dev/test behaviour is closer to it.
            "OPTIONS": {"timeout": 30},
        }
    }

# Emails print to the console instead of sending — no Resend calls
# from a dev machine.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:8000", "http://127.0.0.1:8000"],
)

# Celery tasks run synchronously, in-process, on .delay()/.apply_async() —
# no Redis or worker process needed for `manage.py runserver` or the
# test suite. This is what lets Phase 4-6's Celery-shaped logic
# (expire_attempt_if_stale, issue_certificate, reconciliation) keep
# working locally exactly as it did before Phase 7 added the real
# task/schedule wrappers. prod.py leaves this at base.py's False — a
# real deployment needs a real worker.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
