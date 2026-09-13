import hmac
import logging

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import LeadCaptureForm

logger = logging.getLogger(__name__)


def _safe_next(request, candidate: str) -> str:
    # HTTP_REFERER (and a "next" field) are attacker-influenceable —
    # never redirect() straight to either without this check, or a
    # crafted link becomes an open redirect off this domain.
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidate
    return "/"


@require_POST
def capture_lead(request):
    """The footer/catalog email-capture widget's target — see
    engagement.models.Lead for the reasoning. Redirects back to
    wherever the form was submitted from (HTTP_REFERER), same
    single-page-with-a-flash-message pattern as
    quizbuilder.views.quiz_toggle_active, so this works from any page
    without needing its own dedicated template."""
    form = LeadCaptureForm(request.POST)
    next_url = _safe_next(request, request.POST.get("next") or request.META.get("HTTP_REFERER", ""))

    if not form.is_valid():
        messages.error(request, "That doesn't look like a valid email address.")
        return redirect(next_url)

    email = form.cleaned_data["email"]
    source = (request.POST.get("source") or "")[:100]

    from .models import Lead

    lead, created = Lead.objects.get_or_create(email=email, defaults={"source": source})
    if created:
        from .services import send_lead_welcome_email
        send_lead_welcome_email(lead)

    messages.success(request, "You're on the list — check your inbox for a confirmation.")
    return redirect(next_url)


@csrf_exempt
@require_POST
def run_scheduled_tasks(request):
    """Free-tier workaround for having no real Celery beat running
    (see the Render deploy notes — a single free web service, no
    worker/beat/Redis). Triggered by a GitHub Actions scheduled
    workflow hitting this once a day with a shared secret, same
    pattern as the keep-alive ping. Calling each task function
    directly (not .delay()) runs it synchronously in-process — no
    broker involved either way, works the same whether
    CELERY_TASK_ALWAYS_EAGER is on or off.

    Deliberately scoped to learner-retention and post-certification
    tasks (stalled-learner nudges, expiring-access warnings, drip
    unlocks, enrollment expiry, stale-attempt cleanup, payment
    reconciliation, graduate marketing) — apps.operations' signal-rule
    evaluation/digest tasks are a separate concern, not wired here yet.

    Every task this calls is independently idempotent (dedupe_key on
    EmailLog, capped nudge counts, etc.) — calling this more often
    than once a day would waste compute but not double-send anything.
    """
    token = request.headers.get("X-Cron-Secret", "")
    if not settings.CRON_SECRET or not hmac.compare_digest(token, settings.CRON_SECRET):
        return HttpResponseForbidden("Forbidden")

    from .tasks import (
        advance_compulsory_training_chains_task,
        detect_stalled_learners,
        expire_enrollments,
        expire_stale_attempts,
        reconcile_pending_payments_task,
        remind_live_session,
        send_graduate_marketing_emails_task,
        send_weekly_staff_training_email_task,
        sweep_paystack_transactions_task,
        unlock_dripped_modules,
        warn_expiring_access,
    )

    results = {}
    for name, fn in [
        ("unlock_dripped_modules", unlock_dripped_modules),
        ("detect_stalled_learners", detect_stalled_learners),
        ("warn_expiring_access", warn_expiring_access),
        ("expire_enrollments", expire_enrollments),
        ("remind_live_session", remind_live_session),
        ("expire_stale_attempts", expire_stale_attempts),
        ("reconcile_pending_payments", reconcile_pending_payments_task),
        ("sweep_paystack_transactions", sweep_paystack_transactions_task),
        ("send_graduate_marketing_emails", send_graduate_marketing_emails_task),
        ("send_weekly_staff_training_email", send_weekly_staff_training_email_task),
        ("advance_compulsory_training_chains", advance_compulsory_training_chains_task),
    ]:
        try:
            results[name] = fn() or "ok"
        except Exception as exc:  # noqa: BLE001 — one task failing must not block the rest
            logger.error("run_scheduled_tasks: %s failed: %s", name, exc)
            results[name] = f"error: {exc}"

    return JsonResponse({"ran": results})
