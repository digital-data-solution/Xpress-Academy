from django.contrib import admin
from django.utils import timezone

from .models import SupportMessage, SupportTicket
from .services import notify_learner_of_staff_reply


class SupportMessageInline(admin.TabularInline):
    """Shows the whole conversation and doubles as the reply box: an
    empty new row here, filled in and saved, becomes a STAFF message
    and emails the learner — see SupportTicketAdmin.save_formset.
    Existing rows stay technically editable (this is a trusted staff
    console, same trust level as the rest of the admin), but the
    normal path is "leave old rows alone, fill the blank one at the
    bottom." """

    model = SupportMessage
    extra = 1
    fields = ["sender_badge", "body", "created_at"]
    readonly_fields = ["sender_badge", "created_at"]
    ordering = ["created_at"]

    def sender_badge(self, obj):
        if not obj or not obj.pk:
            return "(new — saving this as staff)"
        if obj.sender_type == SupportMessage.Sender.STAFF and obj.staff_user:
            return f"Staff — {obj.staff_user.email}"
        return obj.get_sender_type_display()

    sender_badge.short_description = "From"


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ["subject", "user", "status", "escalated_at", "last_message_at", "created_at"]
    list_filter = ["status"]
    search_fields = ["subject", "user__email"]
    autocomplete_fields = ["user"]
    readonly_fields = ["escalated_at"]
    inlines = [SupportMessageInline]
    actions = ["mark_resolved"]

    def save_formset(self, request, form, formset, change):
        if formset.model is not SupportMessage:
            return super().save_formset(request, form, formset, change)

        instances = formset.save(commit=False)
        ticket = form.instance
        newly_created = []
        for instance in instances:
            is_new = instance.pk is None
            if is_new:
                if not instance.body.strip():
                    continue  # the always-present blank extra row — nothing typed, skip it
                instance.sender_type = SupportMessage.Sender.STAFF
                instance.staff_user = request.user
            instance.save()
            if is_new:
                newly_created.append(instance)
        formset.save_m2m()
        for obj in formset.deleted_objects:
            obj.delete()

        if newly_created:
            for message in newly_created:
                notify_learner_of_staff_reply(message)
            ticket.status = SupportTicket.Status.AWAITING_LEARNER
            ticket.last_message_at = timezone.now()
            ticket.save(update_fields=["status", "last_message_at", "updated_at"])

    @admin.action(description="Mark selected as RESOLVED")
    def mark_resolved(self, request, queryset):
        count = queryset.update(status=SupportTicket.Status.RESOLVED)
        self.message_user(request, f"{count} ticket(s) marked resolved.")
