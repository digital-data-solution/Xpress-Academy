from django.contrib import admin

from .models import EmailLog, LiveSession


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ["to_email", "template_key", "subject", "status", "created_at", "sent_at"]
    list_filter = ["status", "template_key"]
    search_fields = ["to_email", "subject", "dedupe_key"]
    readonly_fields = [
        "user", "to_email", "template_key", "subject", "status",
        "provider_id", "error", "sent_at", "dedupe_key",
    ]

    def has_add_permission(self, request):
        # Every row comes from send_email() — not authored in admin.
        return False


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "starts_at", "duration_minutes", "is_cancelled"]
    list_filter = ["course", "is_cancelled"]
    search_fields = ["title", "course__title"]
    autocomplete_fields = ["course", "recording_lesson"]
