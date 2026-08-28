from django.contrib import admin
from django.utils import timezone

from .models import Cohort, Enrollment, LessonProgress
from .services import get_progress_percent


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "starts_at", "ends_at", "capacity", "is_founding", "enrollment_count"]
    list_filter = ["course", "is_founding"]
    search_fields = ["name", "course__title"]

    def enrollment_count(self, obj):
        return obj.enrollments.count()

    enrollment_count.short_description = "Enrollments"


class LessonProgressInline(admin.TabularInline):
    model = LessonProgress
    extra = 0
    fields = ["lesson", "watched_seconds", "completed_at"]
    readonly_fields = ["lesson", "watched_seconds", "completed_at"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Progress rows are created by the learner's own activity
        # (mark-complete view), not authored in admin.
        return False


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "user", "course", "status", "source", "cohort",
        "started_at", "expires_at", "progress_display", "last_activity_at",
    ]
    list_filter = ["status", "source", "course"]
    search_fields = ["user__email", "course__title"]
    autocomplete_fields = ["user", "course", "cohort"]
    readonly_fields = ["content_version_at_enrollment", "started_at", "completed_at", "last_activity_at"]
    inlines = [LessonProgressInline]
    actions = ["revoke_enrollment", "reactivate_enrollment", "resend_training_welcome_email"]

    fieldsets = (
        (None, {"fields": ("user", "course", "cohort", "status", "source")}),
        ("Access window", {"fields": ("started_at", "expires_at", "completed_at", "last_activity_at")}),
        ("System", {"fields": ("content_version_at_enrollment",)}),
    )

    def progress_display(self, obj):
        return f"{get_progress_percent(obj)}%"

    progress_display.short_description = "Progress"

    @admin.action(description="Revoke selected enrollments")
    def revoke_enrollment(self, request, queryset):
        updated = queryset.update(status=Enrollment.Status.REVOKED)
        self.message_user(request, f"{updated} enrollment(s) revoked.")

    @admin.action(description="Reactivate selected enrollments")
    def reactivate_enrollment(self, request, queryset):
        updated = queryset.update(status=Enrollment.Status.ACTIVE, last_activity_at=timezone.now())
        self.message_user(request, f"{updated} enrollment(s) reactivated.")

    @admin.action(description="Resend the 'your training is ready' email")
    def resend_training_welcome_email(self, request, queryset):
        # Runs server-side, inside the real deployed process — same
        # reason CertificateAdmin.regenerate_pdf and
        # CourseAdmin.resend_publish_webhook exist: a one-off command
        # run from a developer's laptop only has whatever env vars
        # were manually typed into that terminal (DATABASE_URL alone,
        # typically), never Render's actual RESEND_API_KEY. This
        # action has no such gap. Clears any existing EmailLog for the
        # dedupe_key first, since send_email() otherwise treats an
        # already-SENT log as a no-op — the whole point of this
        # action is to force a real resend.
        from apps.engagement.models import EmailLog

        from apps.accounts.signal_receivers import _send_welcome_to_training_email

        count = 0
        for enrollment in queryset.select_related("user", "course"):
            EmailLog.objects.filter(
                dedupe_key=f"chain_unlocked:{enrollment.user_id}:{enrollment.course_id}"
            ).delete()
            _send_welcome_to_training_email(enrollment.user, enrollment.course)
            count += 1
        self.message_user(request, f"Resent the training-ready email for {count} enrollment(s).")


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "lesson", "watched_seconds", "completed_at"]
    list_filter = ["completed_at", "lesson__module__course"]
    search_fields = ["enrollment__user__email", "lesson__title"]
