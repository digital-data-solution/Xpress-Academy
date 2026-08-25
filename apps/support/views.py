from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .faq import FAQ_ENTRIES
from .forms import NewTicketForm, ReplyForm
from .models import SupportTicket
from .services import post_learner_message


@login_required
def inbox(request):
    if request.method == "POST":
        form = NewTicketForm(request.POST)
        if form.is_valid():
            from apps.organizations.models import Organization

            ticket = SupportTicket.objects.create(
                organization=Organization.objects.first(),
                user=request.user,
                subject=form.cleaned_data["subject"],
            )
            post_learner_message(ticket, form.cleaned_data["body"])
            return redirect("support:thread", ticket_id=ticket.pk)
    else:
        form = NewTicketForm()

    tickets = SupportTicket.objects.filter(user=request.user)
    return render(request, "support/inbox.html", {"form": form, "tickets": tickets, "faq_entries": FAQ_ENTRIES})


@login_required
def thread(request, ticket_id):
    ticket = get_object_or_404(SupportTicket, pk=ticket_id, user=request.user)

    if request.method == "POST":
        if ticket.status == SupportTicket.Status.RESOLVED:
            messages.info(request, "This ticket is marked resolved — start a new one if you need anything else.")
            return redirect("support:thread", ticket_id=ticket.pk)
        form = ReplyForm(request.POST)
        if form.is_valid():
            post_learner_message(ticket, form.cleaned_data["body"])
            return redirect("support:thread", ticket_id=ticket.pk)
    else:
        form = ReplyForm()

    return render(request, "support/thread.html", {"ticket": ticket, "thread_messages": ticket.messages.all(), "form": form})
