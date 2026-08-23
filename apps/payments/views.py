from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Course
from apps.enrollment.models import Enrollment

from .middleware import get_active_partner
from .services import CouponInvalid, PaymentInitError, initialize_payment, verify_and_grant


@login_required
def checkout(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    existing = Enrollment.objects.filter(user=request.user, course=course).first()
    if existing and existing.status in (Enrollment.Status.ACTIVE, Enrollment.Status.COMPLETED):
        messages.info(request, "You already have access to this course.")
        return redirect("enrollment:curriculum", course_slug=course.slug)

    # Build spec §10: "Email verification required before enrollment
    # activates." Checked here, not at signup — a learner can still
    # browse/log in unverified, they just can't pay until confirmed.
    if not request.user.profile.email_verified:
        return render(request, "payments/verify_required.html", {"course": course})

    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code", "").strip() or None
        partner = get_active_partner(request)

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
                attribution_source=attribution_source or "",
            )
        except CouponInvalid as exc:
            return render(request, "payments/checkout.html", {"course": course, "error": str(exc)})
        except PaymentInitError:
            return render(request, "payments/checkout.html", {
                "course": course,
                "error": "We couldn't start checkout right now. Please try again shortly.",
            })
        return redirect(authorization_url)

    return render(request, "payments/checkout.html", {"course": course})


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

    messages.success(request, f"You're enrolled in {payment.course.title}.")
    return redirect("enrollment:curriculum", course_slug=payment.course.slug)
