from django.contrib import admin
from django.core.files.base import ContentFile

from .models import Certificate, CertificateSequence
from .pdf import build_certificate_pdf
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
    actions = ["revoke_selected", "regenerate_pdf"]

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

    @admin.action(description="Regenerate PDF for selected certificates")
    def regenerate_pdf(self, request, queryset):
        # Runs in the request/response cycle on the actual server
        # (Render), not on whoever's local machine happens to run a
        # management command — so it always uses the real storage
        # backend/credentials, not whatever's (or isn't) on a
        # laptop's local .env. Needed once already: a certificate
        # issued before Supabase Storage was wired had to be re-saved
        # through the real backend to stop 404ing; also useful any
        # time the PDF's own design changes.
        count = 0
        for cert in queryset:
            pdf_bytes = build_certificate_pdf(cert)
            cert.pdf.save(f"{cert.serial}.pdf", ContentFile(pdf_bytes), save=True)
            count += 1
        self.message_user(request, f"{count} certificate PDF(s) regenerated.")


@admin.register(CertificateSequence)
class CertificateSequenceAdmin(admin.ModelAdmin):
    list_display = ["audience_code", "year", "last_number"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
