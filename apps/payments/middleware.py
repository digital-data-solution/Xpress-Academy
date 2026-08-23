"""Referral capture — build spec §9: "A visitor arriving at
/courses/<slug>/?ref=CODE gets the code stored in session for 30
days." Implemented as middleware (not tied to a specific view) so a
referral link works no matter which page it lands on — including the
Phase 8 public sales pages.

Two independent referral mechanisms share the same ?ref= param —
Partner (build spec §9, veterinary-clinic-style referrers) and
Instructor (Phase 10, an instructor's own marketing link). They're
looked up and stored under separate session keys so a code collision
between the two tables (unlikely, but not impossible — they're
different models) can't cross-attribute a sale to the wrong party.
"""

from django.utils import timezone

from .models import Partner

PARTNER_SESSION_KEY = "partner_ref"
INSTRUCTOR_SESSION_KEY = "instructor_ref"
CAPTURE_DAYS = 30


class ReferralCaptureMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        code = request.GET.get("ref")
        if code:
            expires = (timezone.now() + timezone.timedelta(days=CAPTURE_DAYS)).isoformat()
            if Partner.objects.filter(referral_code=code, is_active=True).exists():
                request.session[PARTNER_SESSION_KEY] = {"code": code, "expires": expires}

            # Local import: apps.instructors depends on apps.payments
            # (Payment.attributed_instructor), so importing at module
            # level here would be circular.
            from apps.instructors.models import Instructor
            if Instructor.objects.filter(referral_code=code).exists():
                request.session[INSTRUCTOR_SESSION_KEY] = {"code": code, "expires": expires}

        return self.get_response(request)


def get_active_partner(request) -> Partner | None:
    """Called at checkout time to attribute the sale, if a referral
    is still live in the session."""
    data = request.session.get(PARTNER_SESSION_KEY)
    if not data:
        return None
    if timezone.now() > timezone.datetime.fromisoformat(data["expires"]):
        del request.session[PARTNER_SESSION_KEY]
        return None
    return Partner.objects.filter(referral_code=data["code"], is_active=True).first()
