from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "from_email", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug", "from_email"]
    prepopulated_fields = {"slug": ("name",)}
