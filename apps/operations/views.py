from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.organizations.models import Organization

from .analytics import build_growth_context
from .models import Signal
from .services import dismiss_signal, get_open_signals, resolve_signal, snooze_signal


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
