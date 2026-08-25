import hmac
import logging

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)


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

    Deliberately scoped to the engagement app's own learner-retention
    tasks (stalled-learner nudges, expiring-access warnings, drip
    unlocks, enrollment expiry, stale-attempt cleanup, payment
    reconciliation) — apps.operations' signal-rule evaluation/digest
    tasks are a separate concern, not wired here yet.

    Every task this calls is independently idempotent (dedupe_key on
    EmailLog, capped nudge counts, etc.) — calling this more often
    than once a day would waste compute but not double-send anything.
    """
    token = request.headers.get("X-Cron-Secret", "")
    if not settings.CRON_SECRET or not hmac.compare_digest(token, settings.CRON_SECRET):
        return HttpResponseForbidden("Forbidden")

    from .tasks import (
        detect_stalled_learners,
        expire_enrollments,
        expire_stale_attempts,
        reconcile_pending_payments_task,
        remind_live_session,
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
    ]:
        try:
            results[name] = fn() or "ok"
        except Exception as exc:  # noqa: BLE001 — one task failing must not block the rest
            logger.error("run_scheduled_tasks: %s failed: %s", name, exc)
            results[name] = f"error: {exc}"

    return JsonResponse({"ran": results})
