import hmac
import logging

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization
from apps.payments.models import Payment

from .analytics import build_growth_context
from .models import Signal
from .services import dismiss_signal, get_open_signals, resolve_signal, snooze_signal

logger = logging.getLogger(__name__)


@staff_member_required
def ops_queue(request):
    org = Organization.objects.first()
    signals = get_open_signals(org) if org else Signal.objects.none()
    if not request.user.is_superuser:
        # MONEY-category signals (payment reconciliation mismatches, refund
        # spikes, "no payments today") are real financial data — the
        # non-financial "Course Manager" role gets everything else in the
        # queue (quality/learner/instructor/system/etc.) but not this.
        signals = signals.exclude(category=Signal.Category.MONEY)
    return render(request, "operations/queue.html", {"signals": signals})


@staff_member_required
def growth(request):
    if not request.user.is_superuser:
        # Revenue totals/trend — superuser-only. A non-financial staff
        # role (e.g. "Course Manager") should not see platform revenue
        # just by being is_staff=True.
        raise PermissionDenied("The growth dashboard is restricted to superusers.")
    org = Organization.objects.first()
    try:
        days = int(request.GET.get("days", 30))
    except ValueError:
        days = 30
    days = days if days in (30, 90) else 30
    context = build_growth_context(org, days=days) if org else {}
    return render(request, "operations/growth.html", context)


@require_POST
@staff_member_required
def ops_act(request, signal_id):
    signal = get_object_or_404(Signal, pk=signal_id)
    if signal.category == Signal.Category.MONEY and not request.user.is_superuser:
        # Belt-and-suspenders: ops_queue already hides these from a
        # non-superuser, but block direct POSTs to this URL too.
        raise PermissionDenied("MONEY-category signals are restricted to superusers.")
    action = request.POST.get("action")
    if action == "resolve":
        resolve_signal(signal, user=request.user)
    elif action == "dismiss":
        dismiss_signal(signal, reason=request.POST.get("reason", ""), user=request.user)
    elif action == "snooze":
        snooze_signal(signal, days=int(request.POST.get("days", 7)))
    return redirect("operations:queue")


@csrf_exempt
@require_GET
def company_stats(request):
    """Read-only, inbound, shared-secret-gated aggregate-only endpoint
    for Xpress Digital & Data Solutions' cross-portfolio "Company
    Overview" dashboard -- Sam's own explicit ask (via that session),
    confirmed directly with him before building, same pattern as
    apps.enrollment.views.call_candidates (built the same day for the
    same dashboard's headcount side).

    Deliberately aggregate-only -- no PII, no per-user rows, nothing an
    instructor/learner-privacy rule would need to redact. Total revenue
    uses the exact same computation as the superuser-only growth
    dashboard (apps.operations.analytics.build_growth_context's
    total_revenue_kobo: SUM(amount_kobo) over Payment.Status.SUCCESS
    only -- a refund moves a Payment's status to REFUNDED, so it's
    already excluded here, not double-subtracted).
    """
    token = request.headers.get("X-Company-Stats-Secret", "")
    if not settings.COMPANY_STATS_API_SECRET or not hmac.compare_digest(
        token, settings.COMPANY_STATS_API_SECRET
    ):
        return HttpResponseForbidden("Forbidden")

    total_revenue_kobo = (
        Payment.objects.filter(status=Payment.Status.SUCCESS).aggregate(s=Sum("amount_kobo"))["s"] or 0
    )
    active_enrollments = Enrollment.objects.filter(status=Enrollment.Status.ACTIVE).count()

    logger.info(
        "company_stats accessed: total_revenue_naira=%s active_enrollments=%s",
        total_revenue_kobo / 100, active_enrollments,
    )

    return JsonResponse({
        "totalRevenue": total_revenue_kobo / 100,
        "currency": "NGN",
        "activeEnrollments": active_enrollments,
        "period": "all-time",
    })
