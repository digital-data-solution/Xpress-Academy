"""Outbound-only notification fired when a Course goes from draft to
published. Deliberately does NOT send any email or message to any
learner/lead itself — see the module docstring in config.settings
.base.COURSE_PUBLISH_WEBHOOK_URL. This is the one place that builds
and sends the payload; Course.save() calls it, nothing else should.
"""

import logging

import requests
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5


def notify_course_published(course):
    """Fired once, the moment is_published flips False→True (see
    Course.save()). A failed/unreachable webhook must never break
    publishing a course — errors are logged and swallowed, never
    raised, same resilience discipline as run_scheduled_tasks."""
    if not settings.COURSE_PUBLISH_WEBHOOK_URL:
        return  # not configured — nothing to notify, not an error

    course_url = f"{settings.SITE_URL}{reverse('catalog:course_detail', args=[course.slug])}"
    payload = {
        "event": "course.published",
        "course_name": course.title,
        "slug": course.slug,
        "price_ngn": course.price_ngn,
        "pricing_model": course.pricing_model,
        "short_description": course.subtitle,
        "category": course.programme.title if course.programme_id else None,
        "course_url": course_url,
        "published_at": course.published_at.isoformat() if course.published_at else None,
    }
    headers = {
        "X-Webhook-Secret": settings.COURSE_PUBLISH_WEBHOOK_SECRET,
        "Content-Type": "application/json",
    }
    try:
        requests.post(settings.COURSE_PUBLISH_WEBHOOK_URL, json=payload, headers=headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
    except Exception as exc:  # noqa: BLE001 — a failed webhook must never break publishing a course
        logger.error("notify_course_published failed for %s: %s", course.slug, exc)
