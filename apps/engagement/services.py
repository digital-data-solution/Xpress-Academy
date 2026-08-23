"""The email send-gate. Build spec: "All outbound email goes through
apps/engagement/services.py::send_email(). Nothing calls Resend
directly. That function enforces rate limits, writes an EmailLog row,
and honours dedupe_key so a retried Celery task cannot double-send.
This mirrors the emailQueue.js pattern already used in the Xpress
Digital Node backend — same discipline."

Every Celery task in tasks.py, and the direct calls from
apps.payments.services.grant_access / apps.certificates.services.issue_certificate,
go through this one function. Nothing else in the codebase should
import ResendGateway directly.
"""

import logging
import time

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .gateway import ResendError, ResendGateway
from .models import EmailLog

logger = logging.getLogger(__name__)

RATE_LIMIT_WINDOW_SECONDS = 60
MAX_THROTTLE_SLEEP_SECONDS = 3


def _throttle_if_needed():
    """Soft rate limit: smooths a burst rather than hard-rejecting or
    silently dropping (there's no retry-later queue to drop into).
    Sleeping in a Celery task context is fine — it's not blocking a
    web request."""
    window_start = timezone.now() - timezone.timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    recent = EmailLog.objects.filter(status=EmailLog.Status.SENT, sent_at__gte=window_start).count()
    limit = settings.EMAIL_RATE_LIMIT_PER_MINUTE
    if recent >= limit:
        overage = recent - limit + 1
        sleep_for = min(overage * 0.1, MAX_THROTTLE_SLEEP_SECONDS)
        logger.info("send_email: throttling %.1fs (%d sent in the last minute, limit %d)", sleep_for, recent, limit)
        time.sleep(sleep_for)


def _send_via_smtp(*, to_email, from_email, subject, html) -> str:
    """Interim path before Resend is configured — real SMTP against
    whatever mailbox EMAIL_HOST_USER/PASSWORD point at (Gmail with an
    App Password works fine). Constructs the SMTP backend explicitly
    rather than relying on the global EMAIL_BACKEND setting, since
    that's left at the console backend for anything else that might
    call django.core.mail directly — this function is the one place
    that deliberately overrides it. Raises on failure, same contract
    as ResendGateway.send()."""
    from django.core.mail.backends.smtp import EmailBackend
    from django.core.mail.message import EmailMultiAlternatives

    backend = EmailBackend(
        host=settings.EMAIL_HOST, port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER, password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS, fail_silently=False,
    )
    message = EmailMultiAlternatives(subject=subject, body=html, from_email=from_email, to=[to_email], connection=backend)
    message.attach_alternative(html, "text/html")
    message.send()
    return "smtp"


def send_email(*, to_email, template_key, subject, html, user=None, dedupe_key=None, from_email=None) -> EmailLog:
    if dedupe_key:
        existing = EmailLog.objects.filter(dedupe_key=dedupe_key).first()
        if existing and existing.status == EmailLog.Status.SENT:
            return existing  # already sent — a retried task is a no-op, not a resend
        log = existing or EmailLog.objects.create(
            user=user, to_email=to_email, template_key=template_key, subject=subject, dedupe_key=dedupe_key,
        )
    else:
        log = EmailLog.objects.create(
            user=user, to_email=to_email, template_key=template_key, subject=subject,
        )

    from_email = from_email or settings.DEFAULT_FROM_EMAIL_FALLBACK

    # Three tiers: Resend (real, once configured) > SMTP fallback
    # (real, using a mailbox you already have — e.g. Gmail with an App
    # Password) > log-only dev no-op (nothing configured at all).
    if settings.RESEND_API_KEY:
        _throttle_if_needed()
        try:
            response = ResendGateway().send(to_email=to_email, from_email=from_email, subject=subject, html=html)
        except ResendError as exc:
            logger.error("send_email failed (Resend): to=%s template=%s error=%s", to_email, template_key, exc)
            log.status = EmailLog.Status.FAILED
            log.error = str(exc)
            log.save(update_fields=["status", "error", "updated_at"])
            return log
        provider_id = response.get("id", "")

    elif settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        _throttle_if_needed()
        try:
            provider_id = _send_via_smtp(to_email=to_email, from_email=from_email, subject=subject, html=html)
        except Exception as exc:  # noqa: BLE001 — smtplib raises several distinct exception types
            logger.error("send_email failed (SMTP): to=%s template=%s error=%s", to_email, template_key, exc)
            log.status = EmailLog.Status.FAILED
            log.error = str(exc)
            log.save(update_fields=["status", "error", "updated_at"])
            return log

    else:
        # Nothing configured at all — visible in logs rather than a
        # silent no-op.
        logger.info("send_email (no Resend/SMTP configured — not actually sent): to=%s subject=%r", to_email, subject)
        log.status = EmailLog.Status.SENT
        log.provider_id = "dev-noop"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "provider_id", "sent_at", "updated_at"])
        return log

    log.status = EmailLog.Status.SENT
    log.provider_id = provider_id
    log.sent_at = timezone.now()
    log.save(update_fields=["status", "provider_id", "sent_at", "updated_at"])
    return log


# --- Public convenience wrappers for other apps ------------------------
# apps.payments.services.grant_access and
# apps.certificates.services.issue_certificate call these (via a
# function-level import to avoid a load-order cycle) instead of
# reaching into tasks.py or rendering templates themselves — template
# names and subjects are this app's concern, not theirs.

def send_welcome_email(enrollment):
    return send_email(
        to_email=enrollment.user.email,
        user=enrollment.user,
        template_key="welcome",
        subject=f"Welcome to {enrollment.course.title}",
        html=render_to_string("emails/welcome.html", {
            "first_name": enrollment.user.first_name or "there",
            "course_title": enrollment.course.title,
            "site_url": settings.SITE_URL,
        }),
        dedupe_key=f"welcome:{enrollment.id}",
    )


def send_certificate_issued_email(certificate):
    return send_email(
        to_email=certificate.enrollment.user.email,
        user=certificate.enrollment.user,
        template_key="certificate_issued",
        subject=f"Your certificate for {certificate.course_title_snapshot}",
        html=render_to_string("emails/certificate_issued.html", {
            "first_name": certificate.enrollment.user.first_name or "there",
            "course_title": certificate.course_title_snapshot,
            "serial": certificate.serial,
            "site_url": settings.SITE_URL,
        }),
        dedupe_key=f"certificate_issued:{certificate.id}",
    )
