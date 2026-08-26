"""Payment lifecycle per the payments addendum (supersedes build spec
§4's webhook-based rules): verify-on-return + reconciliation, never
webhooks — the Paystack account is shared with Xpress Vet Marketplace
and only has room for one webhook URL, already claimed.

grant_access() is the single choke point every path calls — the
return handler, the reconciliation task, and (for a manual case) an
admin action. No other code creates an Enrollment from a payment.
"""

import logging
import time
import uuid

from django.db import transaction
from django.utils import timezone

from apps.enrollment.models import Cohort, Enrollment

from .gateway import PaystackError, PaystackGateway
from .models import Coupon, CouponAttempt, Payment

logger = logging.getLogger(__name__)

PRODUCT_TAG = "xpress_academy"
MIN_CHARGE_KOBO = 100  # ₦1 — a coupon can discount close to free, never to literally zero

COUPON_LOCKOUT_THRESHOLD = 5
COUPON_LOCKOUT_WINDOW_MINUTES = 15


class CouponInvalid(ValueError):
    pass


def coupon_attempts_locked_out(user) -> bool:
    """A short, human-readable code space (e.g. "LAUNCH20") is
    genuinely guessable given enough unlimited attempts — checkout
    previously let anyone try as many codes as they wanted, no limit
    at all. Same lockout shape as apps.accounts.forms
    .RateLimitedAuthenticationForm: N failures in a window blocks
    further attempts, regardless of whether the next guess would have
    worked. Does NOT block checkout itself — only attempting a coupon
    code; a locked-out user can still pay full price."""
    cutoff = timezone.now() - timezone.timedelta(minutes=COUPON_LOCKOUT_WINDOW_MINUTES)
    recent_failures = CouponAttempt.objects.filter(
        user=user, successful=False, created_at__gte=cutoff,
    ).count()
    return recent_failures >= COUPON_LOCKOUT_THRESHOLD


def record_coupon_attempt(user, code: str, *, successful: bool) -> None:
    CouponAttempt.objects.create(user=user, code_tried=code.upper().strip(), successful=successful)


class PaymentInitError(Exception):
    pass


def generate_reference(course, user) -> str:
    # XDA- prefix per the addendum: instantly identifiable in a shared
    # Paystack dashboard that also carries Xpress Vet traffic.
    return f"XDA-{course.id}-{user.id}-{uuid.uuid4().hex[:12]}"


def validate_coupon(coupon: Coupon, course) -> None:
    """Raises CouponInvalid with a human-readable reason, or returns None."""
    if not coupon.is_active:
        raise CouponInvalid("This coupon is no longer active.")
    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise CouponInvalid("This coupon isn't valid yet.")
    if coupon.valid_until and now > coupon.valid_until:
        raise CouponInvalid("This coupon has expired.")
    if coupon.max_uses is not None and coupon.times_used >= coupon.max_uses:
        raise CouponInvalid("This coupon has reached its usage limit.")
    if coupon.applies_to_courses.exists() and not coupon.applies_to_courses.filter(pk=course.pk).exists():
        raise CouponInvalid("This coupon doesn't apply to this course.")


def compute_amount_kobo(course, coupon: Coupon | None = None) -> int:
    amount = course.price_ngn * 100
    if coupon:
        if coupon.discount_type == Coupon.DiscountType.PERCENT:
            amount -= amount * coupon.value // 100
        else:  # FIXED — value is already kobo
            amount -= coupon.value
    return max(amount, MIN_CHARGE_KOBO)


def initialize_payment(
    *, user, course, coupon_code=None, partner=None, cohort=None,
    attribution="", attributed_instructor=None, attribution_source="",
    purpose=Payment.Purpose.COURSE_ACCESS, custom_amount_kobo=None,
) -> tuple[Payment, str]:
    """Returns (payment, authorization_url). Raises PaymentInitError if
    Paystack rejects the call — the Payment row still exists, marked
    FAILED, so nothing is lost track of.

    Deliberately NOT wrapped in transaction.atomic: the Payment must
    be created and persisted *before* the Paystack call regardless of
    what happens next, and if this whole function were one atomic
    block, raising PaymentInitError after marking it FAILED would roll
    back the FAILED save AND the original creation — the Payment
    would vanish, exactly the "dangerous direction" the addendum warns
    against. Each write below commits on its own.
    """
    coupon = None
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code.upper().strip()).first()
        if not coupon:
            raise CouponInvalid("Coupon code not found.")
        validate_coupon(coupon, course)

    # custom_amount_kobo: PAY_WHAT_YOU_WANT courses — the buyer's own
    # entered amount, already validated against course.minimum_price_ngn
    # by the caller (checkout()). Still floored at MIN_CHARGE_KOBO —
    # Paystack itself won't process a literal ₦0 charge.
    amount_kobo = max(custom_amount_kobo, MIN_CHARGE_KOBO) if custom_amount_kobo is not None else compute_amount_kobo(course, coupon)
    reference = generate_reference(course, user)

    # Created BEFORE calling Paystack — per the addendum, "a payment
    # that exists on Paystack but not locally is the dangerous
    # direction. Never let that happen."
    payment = Payment.objects.create(
        user=user, course=course, cohort=cohort,
        reference=reference, amount_kobo=amount_kobo,
        coupon=coupon, partner=partner, purpose=purpose,
        # Phase 10 — snapshotted at init time (this is when we know
        # the session's referral state), read back at grant_access
        # time to write the instructor earnings split.
        attribution=attribution, attributed_instructor=attributed_instructor,
        attribution_source=attribution_source,
    )

    callback_url = f"{_site_url()}/checkout/return/"
    metadata = {
        "product": PRODUCT_TAG,
        "course_id": course.id,
        "course_slug": course.slug,
        "user_id": user.id,
        "coupon_code": coupon.code if coupon else None,
        "partner_ref": partner.referral_code if partner else None,
        "purpose": purpose,
    }

    try:
        response = PaystackGateway().initialize_transaction(
            email=user.email, amount_kobo=amount_kobo, reference=reference,
            callback_url=callback_url, metadata=metadata,
        )
    except PaystackError as exc:
        payment.status = Payment.Status.FAILED
        payment.raw_init_response = {"error": str(exc)}
        payment.save(update_fields=["status", "raw_init_response", "updated_at"])
        raise PaymentInitError(str(exc)) from exc

    payment.raw_init_response = response
    payment.save(update_fields=["raw_init_response", "updated_at"])

    authorization_url = response["data"]["authorization_url"]
    return payment, authorization_url


def _site_url():
    from django.conf import settings
    return settings.SITE_URL.rstrip("/")


def _verify_data_matches(payment: Payment, verify_data: dict) -> str | None:
    """Returns None if all checks pass, else a human-readable reason
    they didn't — per addendum §2.3, every one of these is asserted,
    never just the amount."""
    if verify_data.get("status") != "success":
        return f"Paystack reports status={verify_data.get('status')!r}"
    if verify_data.get("amount") != payment.amount_kobo:
        return f"Amount mismatch: expected {payment.amount_kobo}, got {verify_data.get('amount')}"
    if verify_data.get("currency") != "NGN":
        return f"Currency mismatch: {verify_data.get('currency')!r}"
    if verify_data.get("reference") != payment.reference:
        return "Reference mismatch"
    if (verify_data.get("metadata") or {}).get("product") != PRODUCT_TAG:
        return "metadata.product mismatch — not an Academy transaction"
    return None


def verify_and_grant(reference: str) -> tuple[Payment | None, str | None]:
    """The return-handler and reconciliation entry point. reference is
    untrusted input (query string / listed from Paystack) — it only
    says which transaction to check, never what its status is.
    Returns (payment, error_message). error_message is None on success
    (including the idempotent already-SUCCESS case)."""
    payment = Payment.objects.filter(reference=reference).first()
    if not payment:
        logger.warning("verify_and_grant: no local Payment for reference %s", reference)
        return None, "No matching payment found."

    if payment.status == Payment.Status.SUCCESS:
        return payment, None  # idempotent — do not re-verify or re-grant

    try:
        verify_response = PaystackGateway().verify_transaction(reference)
    except PaystackError as exc:
        logger.error("verify_and_grant: Paystack verify failed for %s: %s", reference, exc)
        return payment, "Payment could not be confirmed right now. Please contact support."

    verify_data = verify_response.get("data", {})
    mismatch_reason = _verify_data_matches(payment, verify_data)
    if mismatch_reason:
        payment.status = Payment.Status.FAILED
        payment.raw_verify_response = verify_response
        payment.save(update_fields=["status", "raw_verify_response", "updated_at"])
        logger.warning("verify_and_grant: %s for reference %s", mismatch_reason, reference)
        return payment, "Payment could not be confirmed."

    grant_access(payment, verify_data)
    payment.refresh_from_db()  # grant_access mutates its own re-fetched copy, not this one
    return payment, None


def _create_or_get_enrollment(*, user, course, cohort=None, source, partner=None) -> tuple[Enrollment, bool]:
    """Shared by grant_access (paid) and grant_free_access (FREE /
    CERTIFICATE_PAID courses) — the TIMED-expiry calculation must stay
    identical for both, so it isn't duplicated."""
    enrollment, created = Enrollment.objects.get_or_create(
        user=user, course=course,
        defaults={"cohort": cohort, "source": source, "partner": partner},
    )
    if course.access_type == course.AccessType.TIMED and created:
        months = course.access_months or 0
        enrollment.expires_at = timezone.now() + timezone.timedelta(days=30 * months)
        enrollment.save(update_fields=["expires_at"])
    return enrollment, created


@transaction.atomic
def grant_free_access(*, user, course) -> Enrollment:
    """Entry point for Course.PricingModel.FREE and CERTIFICATE_PAID —
    both grant course access immediately, no payment involved (the
    CERTIFICATE_PAID payment happens later, at certificate time, via
    grant_access with Payment.Purpose.CERTIFICATE). No Payment row at
    all here — there's nothing to reconcile against Paystack for
    something that was never charged."""
    enrollment, created = _create_or_get_enrollment(
        user=user, course=course, source=Enrollment.Source.PURCHASE,
    )
    if created:
        logger.info("grant_free_access: enrolled %s in %s (pricing_model=%s)", user.email, course.title, course.pricing_model)

        def _send_welcome():
            from apps.engagement.services import send_welcome_email
            send_welcome_email(enrollment)

        transaction.on_commit(_send_welcome)
    return enrollment


@transaction.atomic
def grant_access(payment: Payment, verify_data: dict) -> Enrollment | None:
    """The single choke point for anything a successful Payment can
    grant. Every path that can conclude a payment succeeded calls
    this — nothing else creates an Enrollment or issues a
    CERTIFICATE-purpose Certificate from a Payment. Idempotent and
    safe to race (see apps/payments/tests.py's concurrency test).

    Branches on payment.purpose:
    - COURSE_ACCESS (the original, only case before pricing_model
      existed): creates/confirms the Enrollment, same as always.
    - CERTIFICATE: the enrollment already exists and is already free
      (CERTIFICATE_PAID courses grant access via grant_free_access at
      enrollment time) — this just unlocks issuing the Certificate,
      which issue_certificate() otherwise withholds for that pricing
      model. Returns the Enrollment either way so callers have
      somewhere to redirect to.
    """
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status == Payment.Status.SUCCESS:
        return payment.course.enrollments.get(user=payment.user)  # already done, no side effects

    payment.status = Payment.Status.SUCCESS
    payment.paid_at = timezone.now()
    payment.raw_verify_response = verify_data
    payment.save(update_fields=["status", "paid_at", "raw_verify_response", "updated_at"])

    if payment.purpose == Payment.Purpose.CERTIFICATE:
        enrollment = payment.course.enrollments.get(user=payment.user)
        from apps.certificates.services import issue_certificate
        issue_certificate(enrollment, bypass_payment_gate=True)
        logger.info("grant_access: certificate unlocked for %s on %s via payment %s", payment.user.email, payment.course.title, payment.reference)
        return enrollment

    source = Enrollment.Source.PURCHASE
    if payment.coupon:
        source = Enrollment.Source.COUPON
    elif payment.partner:
        source = Enrollment.Source.PARTNER

    enrollment, created = _create_or_get_enrollment(
        user=payment.user, course=payment.course, cohort=payment.cohort,
        source=source, partner=payment.partner,
    )

    if payment.coupon:
        # F() expression, not a Python read-modify-write — the
        # addendum is explicit about this to avoid a lost update under
        # concurrent redemptions of the same coupon.
        from django.db.models import F
        Coupon.objects.filter(pk=payment.coupon_id).update(times_used=F("times_used") + 1)

    if payment.course.instructor_id:
        # Phase 10 — no-op for a first-party course (instructor_id is
        # None). Safe to call inside this same atomic block:
        # record_sale_earnings is itself idempotent (checks for
        # existing entries against this payment first), so a re-run
        # via grant_access's own early-return-on-SUCCESS guard above
        # can never double-write it anyway.
        from apps.instructors.services import record_sale_earnings
        record_sale_earnings(payment)

    logger.info("grant_access: enrolled %s in %s via payment %s", payment.user.email, payment.course.title, payment.reference)

    # Queued outside the transaction — must not fire until the
    # Enrollment/Payment writes above are actually committed, and a
    # failed send here must never roll back the enrollment itself.
    # Local import: apps.engagement.tasks imports apps.payments.services
    # (for the reconciliation Celery tasks), so importing at module
    # level here would be circular.
    def _send_welcome():
        from apps.engagement.services import send_welcome_email
        send_welcome_email(enrollment)

    transaction.on_commit(_send_welcome)

    return enrollment


# --- Reconciliation (the safety net — addendum §2.4) -------------------

def reconcile_pending_payments(*, now=None) -> dict:
    """Intended to run every 10 minutes (Phase 7 Celery beat puts it on
    that schedule; for now it's a management command — see
    apps/payments/management/commands/reconcile_pending_payments.py).
    """
    now = now or timezone.now()
    window_start = now - timezone.timedelta(days=7)
    window_end = now - timezone.timedelta(minutes=5)

    stale_but_recent = Payment.objects.filter(
        status=Payment.Status.PENDING, initialized_at__lte=window_end, initialized_at__gte=window_start,
    ).order_by("initialized_at")[:200]

    too_old = Payment.objects.filter(status=Payment.Status.PENDING, initialized_at__lt=window_start)
    abandoned_count = too_old.update(status=Payment.Status.ABANDONED)

    checked = 0
    granted = 0
    for payment in stale_but_recent:
        _payment, error = verify_and_grant(payment.reference)
        checked += 1
        if error is None:
            granted += 1
        time.sleep(0.2)  # throttle — addendum: "sleep briefly between calls"

    if len(stale_but_recent) >= 200:
        logger.warning("reconcile_pending_payments: hit the 200-per-run cap")

    return {"checked": checked, "granted": granted, "abandoned": abandoned_count}


def sweep_paystack_transactions(*, now=None) -> dict:
    """Daily, 02:00 WAT (config/celery.py). Lists recent Paystack
    successes, filters to Academy transactions only, and flags (never
    auto-grants) any with no matching local SUCCESS Payment — raised
    as a real apps.operations Signal (payment.reconcile_mismatch,
    CRITICAL, INTERRUPT channel) since Phase 11, which is what
    ReconciliationFlag's docstring always said would eventually
    replace it. ReconciliationFlag itself stays in the codebase for
    any historical rows from before Phase 11 shipped."""
    now = now or timezone.now()
    from_dt = now - timezone.timedelta(hours=48)

    flagged = 0
    seen = 0
    page = 1
    while True:
        try:
            response = PaystackGateway().list_transactions(
                from_dt=from_dt, to_dt=now, status="success", page=page, per_page=100
            )
        except PaystackError as exc:
            logger.error("sweep_paystack_transactions: list call failed: %s", exc)
            break

        transactions = response.get("data", [])
        if not transactions:
            break

        for txn in transactions:
            reference = txn.get("reference", "")
            metadata = txn.get("metadata") or {}
            is_academy = reference.startswith("XDA-") or metadata.get("product") == PRODUCT_TAG
            if not is_academy:
                continue  # Xpress Vet's transaction — ignore entirely, never log customer detail
            seen += 1

            local = Payment.objects.filter(reference=reference, status=Payment.Status.SUCCESS).first()
            if local:
                continue

            # Local import: apps.operations.rules imports apps.payments.models
            # (Payment), so importing at module level here would be circular.
            from apps.operations.rules import payment_reconcile_mismatch

            payment_reconcile_mismatch(reference, {"amount": txn.get("amount"), "paid_at": txn.get("paid_at")})
            flagged += 1
            logger.critical("sweep_paystack_transactions: reconciliation mismatch for %s", reference)

        meta = response.get("meta", {})
        if page * 100 >= meta.get("total", 0):
            break
        page += 1

    return {"seen": seen, "flagged": flagged}


def refund_payment(payment: Payment, reason: str) -> Payment:
    """Manual only — addendum §5: never call Paystack's refund API from
    Academy code. Sam issues the refund from the dashboard by hand;
    this just records it and the caller is responsible for revoking
    the Enrollment separately (not done automatically — a refund
    doesn't always mean the learner loses access, that's a judgement call)."""
    payment.status = Payment.Status.REFUNDED
    payment.refunded_at = timezone.now()
    payment.refund_reason = reason
    payment.save(update_fields=["status", "refunded_at", "refund_reason", "updated_at"])

    if payment.course.instructor_id:
        # Phase 10 — build spec §6: "Refunds are debited from the
        # instructor's ledger via REFUND_REVERSAL."
        from apps.instructors.services import reverse_earnings_for_refund
        reverse_earnings_for_refund(payment)

    return payment
