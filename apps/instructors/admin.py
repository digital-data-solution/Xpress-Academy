from django.contrib import admin

from .models import (
    CourseHealth,
    CourseRating,
    CourseReview,
    EarningsEntry,
    Instructor,
    InstructorDocument,
    LearnerInstructorMessage,
    Payout,
    Vertical,
)
from .services import get_instructor_balance, mark_payout_sent


@admin.register(Vertical)
class VerticalAdmin(admin.ModelAdmin):
    list_display = ["name", "domain_reviewer", "requires_legal_review", "is_open_for_applications"]
    list_filter = ["requires_legal_review", "is_open_for_applications"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["domain_reviewer"]


class InstructorDocumentInline(admin.TabularInline):
    model = InstructorDocument
    extra = 0


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = [
        "display_name", "user", "verification_status", "status", "referral_code", "balance_display",
    ]
    list_filter = ["verification_status", "status"]
    search_fields = ["display_name", "user__email", "referral_code"]
    autocomplete_fields = ["user", "verified_by"]
    inlines = [InstructorDocumentInline]
    actions = ["mark_verified"]

    def balance_display(self, obj):
        kobo = get_instructor_balance(obj)
        return f"₦{kobo / 100:,.2f}"

    balance_display.short_description = "Balance"

    @admin.action(description="Mark selected as VERIFIED (does not check documents — review them first)")
    def mark_verified(self, request, queryset):
        from django.utils import timezone
        count = queryset.update(
            verification_status=Instructor.VerificationStatus.VERIFIED,
            verified_by=request.user, verified_at=timezone.now(),
        )
        self.message_user(request, f"{count} instructor(s) marked VERIFIED.")


@admin.register(CourseReview)
class CourseReviewAdmin(admin.ModelAdmin):
    list_display = ["course", "round", "outcome", "reviewer", "submitted_at", "completed_at"]
    list_filter = ["outcome"]
    search_fields = ["course__title"]
    autocomplete_fields = ["course", "reviewer"]
    # Append-only per the model's docstring — admin should not let
    # anyone edit a completed round after the fact.
    readonly_fields = ["course", "round", "submitted_at"]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.completed_at:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


@admin.register(EarningsEntry)
class EarningsEntryAdmin(admin.ModelAdmin):
    list_display = ["instructor", "entry_type", "amount_kobo", "course", "created_at"]
    list_filter = ["entry_type", "attribution"]
    search_fields = ["instructor__display_name", "description"]
    autocomplete_fields = ["instructor", "course", "payment", "payout"]

    def has_change_permission(self, request, obj=None):
        return False  # append-only ledger — no edits, ever

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ["instructor", "period_start", "period_end", "amount_kobo", "status", "sent_at"]
    list_filter = ["status"]
    search_fields = ["instructor__display_name", "bank_reference"]
    autocomplete_fields = ["instructor", "approved_by"]
    actions = ["mark_sent"]

    @admin.action(description="Mark selected as SENT (records the payout — does NOT call any bank/transfer API)")
    def mark_sent(self, request, queryset):
        count = 0
        for payout in queryset.filter(status__in=[Payout.Status.DRAFT, Payout.Status.APPROVED]):
            mark_payout_sent(payout, bank_reference=payout.bank_reference or "manual")
            count += 1
        self.message_user(request, f"{count} payout(s) marked sent.")


@admin.register(CourseHealth)
class CourseHealthAdmin(admin.ModelAdmin):
    list_display = ["course", "date", "enrollments_30d", "completion_rate", "refund_rate_30d", "avg_rating"]
    list_filter = ["date"]
    search_fields = ["course__title"]

    def has_add_permission(self, request):
        return False


@admin.register(CourseRating)
class CourseRatingAdmin(admin.ModelAdmin):
    list_display = ["course", "user", "rating", "is_removed", "created_at"]
    list_filter = ["rating", "is_removed"]
    search_fields = ["course__title", "user__email", "review_text"]
    actions = ["remove_for_abuse"]

    @admin.action(description="Remove for abuse (logged)")
    def remove_for_abuse(self, request, queryset):
        count = queryset.update(is_removed=True, removal_reason="Removed for abuse via admin")
        self.message_user(request, f"{count} rating(s) removed.")


@admin.register(LearnerInstructorMessage)
class LearnerInstructorMessageAdmin(admin.ModelAdmin):
    list_display = ["course", "learner", "sender", "created_at"]
    list_filter = ["sender"]
    search_fields = ["course__title", "learner__email", "body"]

    def has_add_permission(self, request):
        return False
