"""Outbound-only notifications fired when a Course goes from draft to
published. Deliberately does NOT send any email or message to any
learner/lead itself — see the module docstrings on
config.settings.base's *_WEBHOOK_URL settings and
Programme.WebhookLine. This is the one place that builds and sends
each payload; Course.save() calls it, nothing else should.

Two independent destinations today, one per Programme.webhook_line —
DIGITAL (Xpress Digital Academy's own campaign system) and VET (Xpress
Vet Marketplace). Adding a third destination later is: one new
WebhookLine choice + one new settings URL/secret pair + one new row in
_TARGETS below — no change to the dispatch logic itself.
"""

import logging

import requests
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 5

# WebhookLine value -> (settings attr for URL, settings attr for secret)
_TARGETS = {
    "DIGITAL": ("COURSE_PUBLISH_WEBHOOK_URL", "COURSE_PUBLISH_WEBHOOK_SECRET"),
    "VET": ("VET_COURSE_PUBLISH_WEBHOOK_URL", "VET_COURSE_PUBLISH_WEBHOOK_SECRET"),
}


def notify_course_published(course):
    """Fired once, the moment is_published flips False→True (see
    Course.save()). Looks up which destination (if any) this course's
    Programme is wired to, and skips entirely for WebhookLine.NONE or
    an unconfigured destination — same fail-open discipline as
    OPS_ALERT_EMAIL/CRON_SECRET elsewhere. A failed/unreachable
    endpoint is logged and swallowed, never raised — must never break
    publishing a course.

    Returns True (sent, got a 2xx), False (attempted but failed — bad
    response or network error, already logged), or None (skipped —
    WebhookLine.NONE, or this destination's URL isn't configured in
    the CURRENT environment). Course.save() ignores this return value;
    it exists so a management command run in an environment that might
    be missing the destination's secret/URL (e.g. a local terminal
    against the prod DB, which has no reason to also carry the prod
    webhook secrets) can tell 'silently skipped' apart from 'actually
    sent' instead of reporting false confidence. See
    resend_vet_webhooks.py, which exists because exactly this silent
    skip happened for real: two local runs of
    apply_vet_blog_credit_and_publish and one of
    fix_pet_owner_education_webhook_line published 26+5 courses
    without ever sending their webhook, because VET_COURSE_PUBLISH_WEBHOOK_URL
    isn't in this project's local .env — only in Render's deployed env."""
    line = course.programme.webhook_line
    target = _TARGETS.get(line)
    if not target:
        return None  # WebhookLine.NONE, or a line with no configured settings pair

    url = getattr(settings, target[0], "")
    secret = getattr(settings, target[1], "")
    if not url:
        return None  # destination not configured in this environment — nothing to send

    course_url = f"{settings.SITE_URL}{reverse('catalog:course_detail', args=[course.slug])}"
    payload = {
        "event": "course.published",
        "line": line,
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
        "X-Webhook-Secret": secret,
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=WEBHOOK_TIMEOUT_SECONDS)
        # requests only raises for network-level failures (DNS, connection
        # refused, timeout) — a 401/404/500 response comes back as a normal
        # Response object with no exception, so it would otherwise look
        # identical to success. Log it explicitly, still without raising.
        if not response.ok:
            logger.error(
                "notify_course_published(%s) got HTTP %s for %s: %s",
                line, response.status_code, course.slug, response.text[:500],
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001 — a failed webhook must never break publishing a course
        logger.error("notify_course_published(%s) failed for %s: %s", line, course.slug, exc)
        return False
