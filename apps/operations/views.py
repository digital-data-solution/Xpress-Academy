from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.organizations.models import Organization

from .models import Signal
from .services import dismiss_signal, get_open_signals, resolve_signal, snooze_signal


@staff_member_required
def ops_queue(request):
    org = Organization.objects.first()
    signals = get_open_signals(org) if org else Signal.objects.none()
    return render(request, "operations/queue.html", {"signals": signals})


@require_POST
@staff_member_required
def ops_act(request, signal_id):
    signal = get_object_or_404(Signal, pk=signal_id)
    action = request.POST.get("action")
    if action == "resolve":
        resolve_signal(signal, user=request.user)
    elif action == "dismiss":
        dismiss_signal(signal, reason=request.POST.get("reason", ""), user=request.user)
    elif action == "snooze":
        snooze_signal(signal, days=int(request.POST.get("days", 7)))
    return redirect("operations:queue")
