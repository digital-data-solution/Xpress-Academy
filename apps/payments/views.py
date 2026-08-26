from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalog.models import Course
from apps.enrollment.models import Enrollment

from .middleware import get_active_partner
from .models import Payment
from .services import (
    CouponInvalid,
    PaymentInitError,
    coupon_attempts_locked_out,
    grant_free_access,
    initialize_payment,
    record_coupon_attempt,
    verify_and_grant,
)


@login_required
def checkout(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    existing = Enrollment.objects.filter(user=request.user, course=course).first()
    if existing and existing.status in (Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED):
        messages.info(request, "You already have access to this course.")
        return redirect("enrollment:curriculum", course_slug=course.slug)

    # Build spec §10: "Email verification required before enrollment
    # activates." Checked here, not at signup — a learner can still
    # browse/log in unverified, they just can't pay (or claim free
    # access) until confirmed.
    if not request.user.profile.email_verified:
        return render(request, "payments/verify_required.html", {"course": course})

    if course.prerequisite_id:
        prereq_done = Enrollment.objects.filter(
            user=request.user, course=course.prerequisite, status=Enrollment.Status.COMPLETED
        ).exists()
        if not prereq_done:
            messages.error(request, f'Finish "{course.prerequisite.title}" first — that unlocks this course.')
            return redirect("catalog:course_detail", slug=course.prerequisite.slug)

    # FREE and CERTIFICATE_PAID both grant course access with no
    # payment at all — the only difference between them shows up
    # later, at certificate time (see checkout_certificate below).
    if course.pricing_model in (Course.PricingModel.FREE, Course.PricingModel.CERTIFICATE_PAID):
        grant_free_access(user=request.user, course=course)
        messages.success(request, f"You're enrolled in {course.title}.")
        return redirect("enrollment:curriculum", course_slug=course.slug)

    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code", "").strip() or None
        partner = get_active_partner(request)

        if coupon_code and coupon_attempts_locked_out(request.user):
            return render(request, "payments/checkout.html", {
                "course": course,
                "error": "Too many invalid coupon attempts. Please wait a few minutes, "
                         "or check out without a coupon code.",
            })

        custom_amount_kobo = None
        if course.pricing_model == Course.PricingModel.PAY_WHAT_YOU_WANT:
            try:
                amount_ngn = int(request.POST.get("amount_ngn", "0") or "0")
            except ValueError:
                amount_ngn = -1
            if amount_ngn < course.minimum_price_ngn:
                return render(request, "payments/checkout.html", {
                    "course": course,
                    "error": f"Enter at least ₦{course.minimum_price_ngn}.",
                })
            if amount_ngn <= 0:
                # Buyer named ₦0 on a course whose minimum really is
                # ₦0 — that's a legitimate free claim under this
                # model, not a payment. Same path as FREE.
                grant_free_access(user=request.user, course=course)
                messages.success(request, f"You're enrolled in {course.title}.")
                return redirect("enrollment:curriculum", course_slug=course.slug)
            custom_amount_kobo = amount_ngn * 100

        # Phase 10 — instructor attribution, determined now (this is
        # when the session's referral state is live) and snapshotted
        # onto the Payment for grant_access() to read back later.
        attribution = attributed_instructor = attribution_source = None
        if course.instructor_id:
            from apps.instructors.services import determine_attribution
            attribution, attributed_instructor, attribution_source = determine_attribution(request, course)

        try:
            payment, authorization_url = initialize_payment(
                user=request.user, course=course, coupon_code=coupon_code, partner=partner,
                attribution=attribution or "", attributed_instructor=attributed_instructor,
                attribution_source=attribution_source or "", custom_amount_kobo=custom_amount_kobo,
            )
        except CouponInvalid as exc:
            if coupon_code:
                record_coupon_attempt(request.user, coupon_code, successful=False)
            return render(request, "payments/checkout.html", {"course": course, "error": str(exc)})
        except PaymentInitError:
            return render(request, "payments/checkout.html", {
                "course": course,
                "error": "We couldn't start checkout right now. Please try again shortly.",
            })
        if coupon_code:
            record_coupon_attempt(request.user, coupon_code, successful=True)
        return redirect(authorization_url)

    return render(request, "payments/checkout.html", {"course": course})


@login_required
def checkout_certificate(request, course_slug):
    """CERTIFICATE_PAID courses only — course access is already free
    (granted at enrollment via checkout() above); this is the second,
    separate payment that unlocks issuing the Certificate once the
    course is actually complete. Mirrors checkout() but with
    Payment.Purpose.CERTIFICATE and no coupon/attribution — a
    certificate purchase isn't a course sale."""
    course = get_object_or_404(Course, slug=course_slug)
    if course.pricing_model != Course.PricingModel.CERTIFICATE_PAID:
        messages.error(request, "This course's certificate isn't paid separately.")
        return redirect("enrollment:curriculum", course_slug=course.slug)

    enrollment = get_object_or_404(Enrollment, user=request.user, course=course)
    if enrollment.status != Enrollment.Status.COMPLETED:
        messages.info(request, "Finish the course first — then you can get your certificate.")
        return redirect("enrollment:curriculum", course_slug=course.slug)

    existing_certificate = getattr(enrollment, "certificate", None)
    if existing_certificate:
        return redirect("certificates:mine", serial=existing_certificate.serial)

    if request.method == "POST":
        try:
            payment, authorization_url = initialize_payment(
                user=request.user, course=course, purpose=Payment.Purpose.CERTIFICATE,
            )
        except PaymentInitError:
            return render(request, "payments/checkout_certificate.html", {
                "course": course,
                "error": "We couldn't start checkout right now. Please try again shortly.",
            })
        return redirect(authorization_url)

    return render(request, "payments/checkout_certificate.html", {"course": course})


def checkout_return(request):
    """The learner lands here after paying — build spec §9/addendum
    §2.3. Never trusts the query string beyond "which reference to
    check"; the actual status always comes from calling Paystack."""
    reference = request.GET.get("reference") or request.GET.get("trxref")
    if not reference:
        return render(request, "payments/return_error.html", {
            "message": "No payment reference was provided.",
        })

    payment, error = verify_and_grant(reference)

    if payment is None:
        return render(request, "payments/return_error.html", {
            "message": "We couldn't find that payment. If you were charged, contact support.",
        })

    if error:
        return render(request, "payments/return_error.html", {
            "message": error,
            "reference": reference,
        })

    if payment.purpose == Payment.Purpose.CERTIFICATE:
        enrollment = payment.course.enrollments.get(user=payment.user)
        certificate = getattr(enrollment, "certificate", None)
        messages.success(request, "Payment received — here's your certificate.")
        if certificate:
            return redirect("certificates:mine", serial=certificate.serial)
        return redirect("enrollment:curriculum", course_slug=payment.course.slug)

    messages.success(request, f"You're enrolled in {payment.course.title}.")
    return redirect("enrollment:curriculum", course_slug=payment.course.slug)
