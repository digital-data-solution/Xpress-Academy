"""Referral capture — build spec §9: "A visitor arriving at
/courses/<slug>/?ref=CODE gets the code stored in session for 30
days." Implemented as middleware (not tied to a specific view) so a
referral link works no matter which page it lands on — including the
Phase 8 public sales pages that don't exist yet."""

from django.utils import timezone

from .models import Partner

SESSION_KEY = "partner_ref"
CAPTURE_DAYS = 30


class ReferralCaptureMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        code = request.GET.get("ref")
        if code:
            if Partner.objects.filter(referral_code=code, is_active=True).exists():
                request.session[SESSION_KEY] = {
                    "code": code,
                    "expires": (timezone.now() + timezone.timedelta(days=CAPTURE_DAYS)).isoformat(),
                }
        return self.get_response(request)


def get_active_partner(request) -> Partner | None:
    """Called at checkout time to attribute the sale, if a referral
    is still live in the session."""
    data = request.session.get(SESSION_KEY)
    if not data:
        return None
    if timezone.now() > timezone.datetime.fromisoformat(data["expires"]):
        del request.session[SESSION_KEY]
        return None
    return Partner.objects.filter(referral_code=data["code"], is_active=True).first()
