from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fk_name = "user"


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "last_name", "is_staff", "is_active", "date_joined"]
    list_filter = ["is_staff", "is_active", "is_superuser"]
    search_fields = ["email", "first_name", "last_name"]
    inlines = [ProfileInline]
    actions = ["reset_two_factor"]

    @admin.action(description="Reset two-factor authentication (owner-side recovery)")
    def reset_two_factor(self, request, queryset):
        # Real gap this closes: self-service disable (accounts:twofactor_disable)
        # requires an already-authenticated session — exactly what's
        # unavailable to someone stuck at the 2FA login prompt with a
        # lost authenticator and no backup codes left. This is the
        # recovery path for THAT person, run by whoever has admin
        # access (them, or someone else with the login itself locked
        # up needs the terminal escape hatch instead — see
        # apps.accounts.management.commands.reset_2fa).
        from django_otp.plugins.otp_static.models import StaticDevice
        from django_otp.plugins.otp_totp.models import TOTPDevice

        reset_count = 0
        for user in queryset:
            totp_deleted, _ = TOTPDevice.objects.filter(user=user).delete()
            static_deleted, _ = StaticDevice.objects.filter(user=user).delete()
            if totp_deleted or static_deleted:
                reset_count += 1
        self.message_user(
            request,
            f"Reset two-factor authentication for {reset_count} account(s) — "
            f"they can log in with just their password now.",
        )

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "learner_type", "state", "country", "created_at"]
    list_filter = ["role", "learner_type", "country", "marketing_opt_in"]
    search_fields = ["user__email", "kennel_name", "vcn_number", "phone"]
    autocomplete_fields = ["user"]
