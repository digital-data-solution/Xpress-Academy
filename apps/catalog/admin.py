from adminsortable2.admin import SortableAdminMixin, SortableInlineAdminMixin
from django.contrib import admin
from django.utils.html import format_html

from .models import Course, Lesson, Module, Programme, Resource


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


@admin.register(Course)
class CourseAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = [
        "title",
        "programme",
        "audience",
        "level",
        "price_ngn",
        "is_published",
        "module_count",
    ]
    list_filter = ["programme", "audience", "level", "is_published", "access_type"]
    search_fields = ["title", "slug", "subtitle"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]
    fieldsets = (
        (None, {"fields": ("organization", "programme", "title", "slug", "subtitle", "description")}),
        ("Media", {"fields": ("cover_image", "promo_video_id")}),
        ("Classification", {"fields": ("audience", "level", "estimated_hours")}),
        ("Pricing & access", {
            "fields": (
                "price_ngn", "compare_at_price_ngn",
                "access_type", "access_months",
                "content_version", "free_update_months",
            )
        }),
        ("Completion", {"fields": ("requires_final_assessment", "pass_mark")}),
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
