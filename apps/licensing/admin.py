from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from .models import DiagnosticAttempt, DiagnosticMockTest, Institution, InstitutionalLicense
from .pdf import build_school_summary_pdf
from .services import bulk_enroll_students_from_csv


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ["name", "proprietor", "state", "license_count", "is_active"]
    list_filter = ["is_active", "state"]
    search_fields = ["name", "proprietor__email"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["proprietor"]

    def license_count(self, obj):
        return obj.licenses.count()

    license_count.short_description = "Licences"


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")


@admin.register(InstitutionalLicense)
class InstitutionalLicenseAdmin(admin.ModelAdmin):
    list_display = [
        "institution", "seats", "seats_used_display", "status", "term_starts_at", "term_ends_at",
    ]
    list_filter = ["status", "institution"]
    search_fields = ["institution__name"]
    filter_horizontal = ["courses"]
    change_form_template = "admin/licensing/institutionallicense/change_form.html"

    def seats_used_display(self, obj):
        return f"{obj.seats_used} / {obj.seats}"

    seats_used_display.short_description = "Seats used"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:license_id>/import-students/",
                self.admin_site.admin_view(self.import_csv_view),
                name="licensing_institutionallicense_import_csv",
            ),
        ]
        return custom + urls

    def import_csv_view(self, request, license_id):
        license = self.get_object(request, license_id)
        if license is None:
            messages.error(request, "Licence not found.")
            return redirect("admin:licensing_institutionallicense_changelist")

        if request.method == "POST":
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                result = bulk_enroll_students_from_csv(license, form.cleaned_data["csv_file"])
                if result.created:
                    messages.success(request, f"{result.created} new student account(s) created and seated.")
                if result.seated_existing_user:
                    messages.success(request, f"{result.seated_existing_user} existing account(s) seated.")
                if result.already_seated:
                    messages.info(request, f"{result.already_seated} row(s) already held a seat — skipped.")
                for err in result.errors[:20]:
                    messages.warning(request, err)
                if len(result.errors) > 20:
                    messages.warning(request, f"...and {len(result.errors) - 20} more row(s) with problems.")
                return redirect("admin:licensing_institutionallicense_change", license_id)
        else:
            form = CSVImportForm()

        return render(
            request,
            "admin/licensing/institutionallicense/import_csv.html",
            {
                "form": form,
                "license": license,
                "opts": self.model._meta,
                "title": f"Import students — {license.institution.name}",
            },
        )


@admin.register(DiagnosticMockTest)
class DiagnosticMockTestAdmin(admin.ModelAdmin):
    list_display = ["title", "bank", "institution", "question_count", "time_limit_minutes", "attempt_count", "is_active"]
    list_filter = ["is_active", "institution", "bank"]
    search_fields = ["title"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["syllabus_topic_filter"]
    readonly_fields = ["share_link_display"]
    change_form_template = "admin/licensing/diagnosticmocktest/change_form.html"

    def attempt_count(self, obj):
        return obj.attempts.filter(submitted_at__isnull=False).count()

    attempt_count.short_description = "Completed attempts"

    def share_link_display(self, obj):
        return f"/diagnostic/{obj.slug}/" if obj.pk else "(save first)"

    share_link_display.short_description = "Share this link"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:test_id>/summary-pdf/",
                self.admin_site.admin_view(self.summary_pdf_view),
                name="licensing_diagnosticmocktest_summary_pdf",
            ),
        ]
        return custom + urls

    def summary_pdf_view(self, request, test_id):
        test = self.get_object(request, test_id)
        if test is None:
            messages.error(request, "Diagnostic not found.")
            return redirect("admin:licensing_diagnosticmocktest_changelist")

        attempts = test.attempts.filter(submitted_at__isnull=False)
        school_name = request.GET.get("school")
        if school_name:
            attempts = attempts.filter(school_name__iexact=school_name)

        pdf_bytes = build_school_summary_pdf(test, attempts)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{test.slug}-summary.pdf"'
        return response


@admin.register(DiagnosticAttempt)
class DiagnosticAttemptAdmin(admin.ModelAdmin):
    list_display = ["student_name", "test", "school_name", "score_percent", "started_at", "submitted_at"]
    list_filter = ["test"]
    search_fields = ["student_name", "student_email", "school_name"]
    readonly_fields = [
        "test", "student_name", "student_email", "school_name", "question_snapshot",
        "started_at", "submitted_at", "score_percent", "topic_breakdown", "report_pdf",
    ]

    def has_add_permission(self, request):
        # Attempts are created by a prospect taking the diagnostic, not authored in admin.
        return False
