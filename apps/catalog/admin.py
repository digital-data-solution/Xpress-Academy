from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from django.contrib import admin
from django.utils.html import format_html

from .models import Course, CourseFAQ, Lesson, Module, Programme, Resource


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ["title", "audience", "is_active", "course_count"]
    list_filter = ["audience", "is_active", "organization"]
    search_fields = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}

    def course_count(self, obj):
        return obj.courses.count()

    course_count.short_description = "Courses"


class ModuleInline(SortableInlineAdminMixin, admin.TabularInline):
    model = Module
    extra = 0
    fields = ["order", "title", "unlock_rule", "drip_days", "requires_quiz_pass_to_advance"]
    show_change_link = True


class CourseFAQInline(SortableInlineAdminMixin, admin.TabularInline):
    model = CourseFAQ
    extra = 0
    fields = ["order", "question", "answer"]


@admin.register(Course)
class CourseAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        "title",
        "programme",
        "instructor",
        "review_status",
        "audience",
        "level",
        "price_ngn",
        "is_published",
        "module_count",
    ]
    list_filter = ["programme", "instructor", "review_status", "audience", "level", "is_published", "access_type"]
    search_fields = ["title", "slug", "subtitle"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline, CourseFAQInline]
    autocomplete_fields = ["instructor", "vertical", "reviewed_by", "domain_reviewer"]
    actions = ["resend_publish_webhook"]

    @admin.action(description="Resend course-publish webhook for selected (published) courses")
    def resend_publish_webhook(self, request, queryset):
        """Runs server-side, inside the real deployed process — same
        reason apps.certificates.admin.CertificateAdmin has
        regenerate_pdf: a management command run from a developer's
        laptop only has whatever env vars were manually typed into
        that terminal (e.g. DATABASE_URL alone), never Render's actual
        environment for everything else. This action has no such gap —
        it always reads the real COURSE_PUBLISH_WEBHOOK_URL/
        VET_COURSE_PUBLISH_WEBHOOK_URL wherever it's actually running."""
        from .webhooks import notify_course_published

        published = queryset.filter(is_published=True)
        skipped = queryset.count() - published.count()
        for course in published:
            notify_course_published(course)

        msg = f"Resent publish webhook for {published.count()} course(s)."
        if skipped:
            msg += f" Skipped {skipped} unpublished course(s)."
        self.message_user(request, msg)
    fieldsets = (
        (None, {"fields": ("organization", "programme", "title", "slug", "subtitle", "description")}),
        ("Media", {"fields": ("cover_image", "promo_video_id")}),
        ("Classification", {"fields": ("audience", "level", "estimated_hours")}),
        ("Pricing & access", {
            "fields": (
                "pricing_model", "price_ngn", "minimum_price_ngn", "compare_at_price_ngn",
                "access_type", "access_months",
                "content_version", "free_update_months",
            )
        }),
        ("Completion", {"fields": ("requires_final_assessment", "pass_mark")}),
        ("Sales page", {
            "fields": (
                "sales_headline", "sales_subheadline", "target_audience", "not_for",
                "instructor_bio", "meta_description",
            ),
            "description": "Shown on the public /courses/&lt;slug&gt;/ page. Falls back to subtitle/description when blank.",
        }),
        ("Instructor & review (Phase 10)", {
            "fields": (
                "instructor", "vertical", "review_status", "reviewed_by", "reviewed_at",
                "domain_reviewer", "review_notes", "delisted_reason",
                "last_content_review_at", "next_content_review_due",
            ),
            "description": "is_published can only be True when review_status is APPROVED — enforced by a "
                            "database constraint, not just this form.",
        }),
        ("Publishing", {"fields": ("is_published", "published_at")}),
    )

    def module_count(self, obj):
        return obj.modules.count()

    module_count.short_description = "Modules"


class LessonInline(SortableInlineAdminMixin, admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ["order", "title", "type", "is_preview", "duration_seconds"]
    show_change_link = True


@admin.register(Module)
class ModuleAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["title", "course", "order", "unlock_rule", "lesson_count"]
    list_filter = ["course", "unlock_rule"]
    search_fields = ["title", "course__title"]
    inlines = [LessonInline]

    def lesson_count(self, obj):
        return obj.lessons.count()

    lesson_count.short_description = "Lessons"


@admin.register(Lesson)
class LessonAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["title", "module", "type", "order", "is_preview", "has_video"]
    list_filter = ["type", "is_preview", "module__course"]
    search_fields = ["title", "module__title", "module__course__title"]
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        (None, {"fields": ("module", "order", "title", "slug", "type", "is_preview")}),
        ("Video", {"fields": ("video_provider", "video_id", "duration_seconds")}),
        ("Content", {"fields": ("body", "attachment", "transcript")}),
    )

    def has_video(self, obj):
        return bool(obj.video_id)

    has_video.boolean = True


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ["title", "owner_display", "download_count", "created_at"]
    list_filter = ["course", "module"]
    search_fields = ["title", "description"]

    def owner_display(self, obj):
        target = obj.course or obj.module
        return format_html("{}", target) if target else "—"

    owner_display.short_description = "Attached to"
