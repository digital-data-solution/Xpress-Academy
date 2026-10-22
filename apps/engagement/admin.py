from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path

from .models import EmailLog, Lead, LiveSession, SelarContact


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ["email", "source", "created_at"]
    list_filter = ["source"]
    search_fields = ["email"]


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


class SelarImportForm(forms.Form):
    csv_text = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 12, "style": "width:100%;font-family:monospace"}),
        help_text="Paste Selar's Sales export (CSV, header row included).",
    )
    csv_file = forms.FileField(required=False, help_text="...or upload the exported CSV file.")
    abandoned = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 3, "style": "width:100%"}),
        help_text="One per line, from Selar's abandoned-transaction emails: Full Name <email>",
    )
    send_now = forms.BooleanField(required=False, initial=True, help_text="Send any follow-up emails that are due right away.")


@admin.register(SelarContact)
class SelarContactAdmin(admin.ModelAdmin):
    """Selar has no webhooks, so contacts arrive through the import
    page below (the same logic as the import_selar_contacts command) —
    no shell or database URL needed."""

    list_display = ["email", "name", "status", "status_changed_at", "reference", "reference_verified", "unsubscribed"]
    list_filter = ["status", "reference_verified", "unsubscribed"]
    search_fields = ["email", "name", "reference", "phone"]
    change_list_template = "admin/engagement/selarcontact/change_list.html"

    def get_urls(self):
        return [path("import/", self.admin_site.admin_view(self.import_view), name="engagement_selarcontact_import")] + super().get_urls()

    def import_view(self, request):
        from .selar import import_abandoned, import_csv_text, send_selar_followups, unverified_claims

        form = SelarImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            text = form.cleaned_data["csv_text"]
            if form.cleaned_data["csv_file"]:
                text = form.cleaned_data["csv_file"].read().decode("utf-8-sig")
            counts = import_csv_text(text) if text.strip() else {}
            for line in filter(None, (l.strip() for l in form.cleaned_data["abandoned"].splitlines())):
                try:
                    import_abandoned(line)
                    counts[SelarContact.Status.ABANDONED] = counts.get(SelarContact.Status.ABANDONED, 0) + 1
                except ValueError as exc:
                    messages.error(request, str(exc))
            messages.success(request, f"Imported: {counts}. Contacts now: {SelarContact.objects.count()}.")
            if form.cleaned_data["send_now"]:
                messages.info(request, f"Emails sent now: {send_selar_followups() or 'none due yet'}")
            for c in unverified_claims():
                messages.warning(request, f"Unverified activation: {c.email} used {c.reference}. Check it on Selar.")
            return redirect("admin:engagement_selarcontact_changelist")
        return render(request, "admin/engagement/selarcontact/import.html", {
            **self.admin_site.each_context(request), "form": form, "title": "Import Selar contacts",
            "opts": self.model._meta,
        })
