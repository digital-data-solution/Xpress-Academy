from django.contrib import admin

from .models import CalendarObligation, DigestRun, InterruptBudget, InterruptLog, Signal, SignalRule
from .services import dismiss_signal, resolve_signal, snooze_signal


@admin.register(SignalRule)
class SignalRuleAdmin(admin.ModelAdmin):
    list_display = ["key", "category", "default_severity", "channel", "is_active", "cooldown_days"]
    list_filter = ["category", "channel", "is_active"]
    search_fields = ["key", "description"]


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "severity", "status", "occurrence_count", "last_seen_at"]
    list_filter = ["category", "severity", "status"]
    search_fields = ["title", "key", "detail"]
    readonly_fields = [
        "key", "category", "severity", "title", "detail", "recommended_action", "action_url",
        "subject_type", "subject_id", "dedupe_key", "first_seen_at", "last_seen_at", "occurrence_count",
    ]
    actions = ["resolve_selected", "dismiss_selected", "snooze_7", "snooze_30"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Resolve selected")
    def resolve_selected(self, request, queryset):
        for s in queryset:
            resolve_signal(s, user=request.user)
        self.message_user(request, f"{queryset.count()} resolved.")

    @admin.action(description="Dismiss selected")
    def dismiss_selected(self, request, queryset):
        for s in queryset:
            dismiss_signal(s, reason="Dismissed via admin bulk action", user=request.user)
        self.message_user(request, f"{queryset.count()} dismissed.")

    @admin.action(description="Snooze 7 days")
    def snooze_7(self, request, queryset):
        for s in queryset:
            snooze_signal(s, 7)
        self.message_user(request, f"{queryset.count()} snoozed 7 days.")

    @admin.action(description="Snooze 30 days")
    def snooze_30(self, request, queryset):
        for s in queryset:
            snooze_signal(s, 30)
        self.message_user(request, f"{queryset.count()} snoozed 30 days.")


@admin.register(CalendarObligation)
class CalendarObligationAdmin(admin.ModelAdmin):
    list_display = ["title", "obligation_type", "due_date", "status", "owner"]
    list_filter = ["obligation_type", "status"]
    search_fields = ["title", "notes"]
    autocomplete_fields = ["owner"]


@admin.register(DigestRun)
class DigestRunAdmin(admin.ModelAdmin):
    list_display = ["run_date", "signal_count", "sent_at"]
    readonly_fields = ["organization", "run_date", "sent_at", "signal_count", "rendered_html", "email_log"]

    def has_add_permission(self, request):
        return False


@admin.register(InterruptLog)
class InterruptLogAdmin(admin.ModelAdmin):
    list_display = ["signal", "sent_date", "created_at"]

    def has_add_permission(self, request):
        return False


@admin.register(InterruptBudget)
class InterruptBudgetAdmin(admin.ModelAdmin):
    list_display = ["organization", "date", "count"]

    def has_add_permission(self, request):
        return False
