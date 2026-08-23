"""Instructor marketplace business logic. HARD STOP 3 (see models.py's
module docstring) governs this file specifically: earnings-writing
functions here are safe to exist in code, but must not be wired into
a live money path (i.e. called from apps.payments.services.grant_access)
until the review/publication gate is proven — see
apps.catalog.tests.TestPublicationGate and apps.instructors.tests for
that proof, and README for the wiring status.
"""

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import CourseReview, EarningsEntry, Instructor, Payout


def get_instructor_balance(instructor: Instructor) -> int:
    """Kobo. Always computed — SUM(amount_kobo), never a stored field.
    Build spec: "Balance is always computed... never stored."

    Only entry types that represent the instructor's own payable claim
    count: INSTRUCTOR_EARNING, REFUND_REVERSAL, ADJUSTMENT, PAYOUT_SENT.
    SALE_GROSS and PLATFORM_FEE are accounting/audit entries about the
    whole sale, not money owed to the instructor — summing them in too
    double-counts (gross minus platform fee already nets out to the
    instructor's share via INSTRUCTOR_EARNING, so including SALE_GROSS
    as well overstates the balance by the platform's own cut)."""
    payable_types = [
        EarningsEntry.EntryType.INSTRUCTOR_EARNING,
        EarningsEntry.EntryType.REFUND_REVERSAL,
        EarningsEntry.EntryType.ADJUSTMENT,
        EarningsEntry.EntryType.PAYOUT_SENT,
    ]
    total = EarningsEntry.objects.filter(
        instructor=instructor, entry_type__in=payable_types
    ).aggregate(total=Sum("amount_kobo"))["total"]
    return total or 0


def determine_attribution(request, course) -> tuple[str, "Instructor | None", str]:
    """Build spec §2 Attribution logic: "?ref=<instructor_code> stored
    in session for 30 days. If a purchase of that instructor's course
    occurs while the code is live → OWN_TRAFFIC. Otherwise →
    PLATFORM_TRAFFIC. Last-touch wins." Returns
    (attribution, attributed_instructor, attribution_source).
    """
    from apps.payments.models import Payment

    ref_data = request.session.get("instructor_ref")
    if ref_data:
        expires = timezone.datetime.fromisoformat(ref_data["expires"])
        if timezone.now() <= expires:
            instructor = Instructor.objects.filter(referral_code=ref_data["code"]).first()
            if instructor:
                if course.instructor_id == instructor.id:
                    return Payment.Attribution.OWN_TRAFFIC, instructor, Payment.AttributionSource.REFERRAL_LINK
                return Payment.Attribution.PLATFORM_TRAFFIC, instructor, Payment.AttributionSource.REFERRAL_LINK
        else:
            del request.session["instructor_ref"]

    if course.instructor_id:
        return Payment.Attribution.PLATFORM_TRAFFIC, None, Payment.AttributionSource.DIRECT
    return "", None, Payment.AttributionSource.DIRECT


@transaction.atomic
def record_sale_earnings(payment) -> list[EarningsEntry]:
    """Writes the SALE_GROSS / PLATFORM_FEE / INSTRUCTOR_EARNING triad
    for one successful Payment against an instructor-owned course.
    No-op (returns []) for a first-party course (instructor is None) —
    there's no one to pay out. Idempotent: does nothing if entries
    for this payment already exist.

    NOT currently called from apps.payments.services.grant_access —
    see this module's docstring (HARD STOP 3). Callable directly (e.g.
    from admin, or a backfill command) once Sam is ready to wire it in.
    """
    course = payment.course
    if not course.instructor_id:
        return []
    if EarningsEntry.objects.filter(payment=payment).exists():
        return list(EarningsEntry.objects.filter(payment=payment))

    instructor = course.instructor
    rate = (
        instructor.own_traffic_rate
        if payment.attribution == payment.Attribution.OWN_TRAFFIC
        else instructor.platform_traffic_rate
    )
    gross = payment.amount_kobo
    instructor_share = int(gross * rate / 100)
    platform_share = gross - instructor_share

    entries = [
        EarningsEntry.objects.create(
            organization=course.organization, instructor=instructor, course=course, payment=payment,
            entry_type=EarningsEntry.EntryType.SALE_GROSS, amount_kobo=gross,
            attribution=payment.attribution, rate_applied=rate,
            description=f"Sale of {course.title} — {payment.reference}",
        ),
        EarningsEntry.objects.create(
            organization=course.organization, instructor=instructor, course=course, payment=payment,
            entry_type=EarningsEntry.EntryType.PLATFORM_FEE, amount_kobo=-platform_share,
            attribution=payment.attribution, rate_applied=rate,
            description=f"Platform fee — {payment.reference}",
        ),
        EarningsEntry.objects.create(
            organization=course.organization, instructor=instructor, course=course, payment=payment,
            entry_type=EarningsEntry.EntryType.INSTRUCTOR_EARNING, amount_kobo=instructor_share,
            attribution=payment.attribution, rate_applied=rate,
            description=f"Earning — {payment.reference}",
        ),
    ]
    return entries


@transaction.atomic
def reverse_earnings_for_refund(payment) -> EarningsEntry | None:
    """Build spec §6: "Refunds are debited from the instructor's
    ledger via REFUND_REVERSAL." Reverses only the INSTRUCTOR_EARNING
    portion — the platform fee isn't clawed back from the instructor,
    consistent with how the sale was split."""
    original = EarningsEntry.objects.filter(payment=payment, entry_type=EarningsEntry.EntryType.INSTRUCTOR_EARNING).first()
    if not original:
        return None
    if EarningsEntry.objects.filter(payment=payment, entry_type=EarningsEntry.EntryType.REFUND_REVERSAL).exists():
        return None  # idempotent
    return EarningsEntry.objects.create(
        organization=original.organization, instructor=original.instructor, course=original.course, payment=payment,
        entry_type=EarningsEntry.EntryType.REFUND_REVERSAL, amount_kobo=-original.amount_kobo,
        attribution=original.attribution, rate_applied=original.rate_applied,
        description=f"Refund reversal — {payment.reference}",
    )


def generate_payout(instructor: Instructor, period_start, period_end, approved_by=None) -> Payout:
    """Build spec §2: "Payouts are manual. Generate the statement, Sam
    reviews, Sam pays by bank transfer, Sam marks it sent." This
    creates the DRAFT Payout and computes the amount from the ledger —
    it does not itself move money or write the PAYOUT_SENT entry;
    mark_payout_sent() does that once Sam confirms the transfer."""
    entries = EarningsEntry.objects.filter(
        instructor=instructor, created_at__date__gte=period_start, created_at__date__lte=period_end,
    )
    gross = sum(e.amount_kobo for e in entries if e.entry_type == EarningsEntry.EntryType.SALE_GROSS)
    payable_types = {
        EarningsEntry.EntryType.INSTRUCTOR_EARNING,
        EarningsEntry.EntryType.REFUND_REVERSAL,
        EarningsEntry.EntryType.ADJUSTMENT,
    }
    net = sum(e.amount_kobo for e in entries if e.entry_type in payable_types)

    return Payout.objects.create(
        instructor=instructor, period_start=period_start, period_end=period_end,
        gross_kobo=max(gross, 0), amount_kobo=max(net, 0), approved_by=approved_by,
    )


@transaction.atomic
def mark_payout_sent(payout: Payout, bank_reference: str) -> Payout:
    payout.status = Payout.Status.SENT
    payout.bank_reference = bank_reference
    payout.sent_at = timezone.now()
    payout.save(update_fields=["status", "bank_reference", "sent_at"])
    EarningsEntry.objects.create(
        organization=payout.instructor.organization, instructor=payout.instructor, payout=payout,
        entry_type=EarningsEntry.EntryType.PAYOUT_SENT, amount_kobo=-payout.amount_kobo,
        description=f"Payout sent — {bank_reference}",
    )
    return payout


def submit_course_for_review(course, submitted_by=None) -> CourseReview:
    """Locks editing (callers should check review_status before
    allowing edits — the /teach/ views do) and opens a new review
    round. Reviews are append-only — see CourseReview's docstring."""
    round_number = CourseReview.objects.filter(course=course).count() + 1
    review = CourseReview.objects.create(course=course, reviewer=submitted_by, round=round_number, submitted_at=timezone.now())
    course.review_status = course.ReviewStatus.SUBMITTED
    course.save(update_fields=["review_status"])
    return review


def complete_review(review: CourseReview, outcome: str, reviewer, notes_to_instructor="", internal_notes="", checklist=None):
    review.outcome = outcome
    review.completed_at = timezone.now()
    review.reviewer = reviewer
    review.notes_to_instructor = notes_to_instructor
    review.internal_notes = internal_notes
    review.checklist = checklist or {}
    review.save()

    course = review.course
    if outcome == CourseReview.Outcome.APPROVED:
        course.review_status = course.ReviewStatus.APPROVED
        course.reviewed_by = reviewer
        course.reviewed_at = timezone.now()
        course.last_content_review_at = timezone.now()
    elif outcome == CourseReview.Outcome.CHANGES_REQUESTED:
        course.review_status = course.ReviewStatus.CHANGES_REQUESTED
    else:
        course.review_status = course.ReviewStatus.DRAFT  # rejected — back to the drawing board, not delisted
    course.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "last_content_review_at"])
    return review
