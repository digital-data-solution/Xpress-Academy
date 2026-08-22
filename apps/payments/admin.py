from django.contrib import admin
from django.utils import timezone

from .models import Coupon, Partner, Payment, ReconciliationFlag
from .services import refund_payment


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "referral_code", "commission_percent", "is_active", "payment_count"]
    list_filter = ["is_active", "state"]
    search_fields = ["name", "referral_code", "email"]
    prepopulated_fields = {"referral_code": ("name",)}

    def payment_count(self, obj):
        return obj.payments.filter(status=Payment.Status.SUCCESS).count()

    payment_count.short_description = "Successful payments"


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ["code", "discount_type", "value", "times_used", "max_uses", "is_active", "valid_until"]
    list_filter = ["discount_type", "is_active"]
    search_fields = ["code"]
    filter_horizontal = ["applies_to_courses"]
    readonly_fields = ["times_used"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["reference", "user", "course", "amount_kobo", "status", "initialized_at", "paid_at"]
    list_filter = ["status", "provider"]
    search_fields = ["reference", "user__email", "course__title"]
    autocomplete_fields = ["user", "course"]
    readonly_fields = [
        "reference", "amount_kobo", "currency", "initialized_at", "paid_at",
        "raw_init_response", "raw_verify_response",
    ]
    actions = ["mark_refunded"]

    def has_add_permission(self, request):
        # Payments are created by initialize_payment(), not authored in admin.
        return False

    @admin.action(description="Mark selected as refunded (does NOT call Paystack — see payments addendum §5)")
    def mark_refunded(self, request, queryset):
        count = 0
        for payment in queryset.filter(status=Payment.Status.SUCCESS):
            refund_payment(payment, reason="Marked refunded via admin bulk action")
            count += 1
        self.message_user(
            request,
            f"{count} payment(s) marked refunded locally. Issue the actual refund from the Paystack "
            f"dashboard by hand — this never calls Paystack's refund API.",
        )


@admin.register(ReconciliationFlag)
class ReconciliationFlagAdmin(admin.ModelAdmin):
    list_display = ["reference", "reason", "is_resolved", "created_at"]
    list_filter = ["is_resolved"]
    search_fields = ["reference", "reason"]
    readonly_fields = ["reference", "reason", "raw_data", "created_at"]
    actions = ["resolve_selected"]

    @admin.action(description="Mark selected as resolved")
    def resolve_selected(self, request, queryset):
        count = queryset.filter(is_resolved=False).update(
            is_resolved=True, resolved_at=timezone.now(), resolved_by=request.user,
        )
        self.message_user(request, f"{count} flag(s) marked resolved.")
