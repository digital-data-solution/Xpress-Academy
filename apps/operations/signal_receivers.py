"""Hooks Celery's own task_failure signal to system.job_failures —
the one rule in rules.py that's event-driven rather than polled.
Wired in apps.py::ready()."""

import logging

from celery.signals import task_failure

logger = logging.getLogger(__name__)


def _on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    try:
        from .rules import system_job_failures
        system_job_failures(task_name=sender.name if sender else "unknown", exception_text=str(exception))
    except Exception:  # noqa: BLE001 — a broken alerting path must never break the app further
        logger.exception("system_job_failures itself failed while handling a task failure")


def connect():
    task_failure.connect(_on_task_failure)
