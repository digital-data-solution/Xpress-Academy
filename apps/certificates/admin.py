from django.contrib import admin

from .models import Certificate, CertificateSequence
from .services import revoke_certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = [
        "serial", "learner_name_snapshot", "course_title_snapshot",
        "final_score", "issued_at", "is_revoked",
    ]
    list_filter = ["is_revoked", "issued_at"]
    search_fields = ["serial", "learner_name_snapshot", "course_title_snapshot"]
    readonly_fields = [
        "enrollment", "serial", "verification_slug", "learner_name_snapshot",
        "course_title_snapshot", "issued_at", "pdf", "final_score",
    ]
    actions = ["revoke_selected"]

    def has_add_permission(self, request):
        # Certificates are issued by issue_certificate() on completion, not authored in admin.
        return False

    @admin.action(description="Revoke selected certificates")
    def revoke_selected(self, request, queryset):
        count = 0
        for cert in queryset.filter(is_revoked=False):
            revoke_certificate(cert, reason="Revoked via admin bulk action")
            count += 1
        self.message_user(request, f"{count} certificate(s) revoked.")


@admin.register(CertificateSequence)
class CertificateSequenceAdmin(admin.ModelAdmin):
    list_display = ["audience_code", "year", "last_number"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
