"""Post-certification marketing for Xpress Vet Marketplace
(xpressvetmarketplace.com) and Xpress Digital & Data Solutions Ltd —
a sister business under the same founder, not part of this codebase.
Built and approved by the owner 2026-08-26, run daily via the same
free-tier cron workaround as every other engagement task (see
apps.engagement.views.run_scheduled_tasks).

Two real gates keep this honest rather than a blind blast:

1. **Consent** — only fires for a learner whose Profile.marketing_opt_in
   is True (the "Send me course updates" checkbox on signup,
   apps/accounts/forms.py — already existed, unused until now). Nobody
   gets this email just for finishing a course; they had to have
   separately said yes to updates when they signed up.
2. **No retroactive blast** — scoped to certificates issued from
   GRADUATE_MARKETING_STARTS_AT onward. Certificates issued before this
   shipped were earned under no expectation of a marketing follow-up;
   backfilling everyone already certified into one big send is a
   separate, real decision the owner would need to make explicitly,
   not something this task should do on its first run.
"""

from django.template.loader import render_to_string
from django.utils import timezone

from apps.catalog.models import Audience

from .models import Certificate

# Fixed, not "now at import time" — so behaviour doesn't shift based on
# when the task happens to first run. Matches this codebase's certificate
# serials / payment amounts in being a deliberate snapshot, not
# recomputed.
GRADUATE_MARKETING_STARTS_AT = timezone.datetime(2026, 8, 26, 0, 0, tzinfo=timezone.get_default_timezone())

XPRESS_VET_URL = "https://xpressvetmarketplace.com"
VET_ONBOARDING_URL = f"{XPRESS_VET_URL}/ProfessionalOnboarding?role=vet"
BUSINESS_TOOLS_URL = f"{XPRESS_VET_URL}/Business"
MARKET_URL = f"{XPRESS_VET_URL}/Market"
LISTINGS_CHANNEL_URL = "https://t.me/XpressVetListings"


def _context_for(certificate: Certificate) -> dict:
    """Picks the audience-specific pitch. GENERAL-audience courses
    (e.g. AI Skills) don't fit either the vet-professional or
    breeder-marketplace pitch, so they get the soft, low-commitment
    CTA only — the public listings channel, not a hard push toward
    either onboarding flow. Flagged as a real product gap when this
    was drafted; kept deliberately soft rather than guessed at."""
    course = certificate.enrollment.course
    user = certificate.enrollment.user
    first_name = user.first_name or certificate.learner_name_snapshot.split(" ")[0]
    base = {
        "first_name": first_name,
        "course_title": certificate.course_title_snapshot,
        "listings_channel_url": LISTINGS_CHANNEL_URL,
    }
    if course.audience == Audience.VET:
        return {
            **base, "variant": "vet",
            "subject": "You're certified — here's your next step",
            "vet_onboarding_url": VET_ONBOARDING_URL,
            "business_tools_url": BUSINESS_TOOLS_URL,
        }
    if course.audience == Audience.BREEDER:
        return {
            **base, "variant": "breeder",
            "subject": "You're certified — here's where that goes to work",
            "market_url": MARKET_URL,
        }
    return {**base, "variant": "general", "subject": "Congratulations on your certification"}


def send_graduate_marketing_emails() -> int:
    """Daily. For every consenting, in-scope certificate not yet
    marketed, sends one Xpress Vet Marketplace intro email — see the
    module docstring for the two gates. Checks EmailLog directly
    (rather than relying solely on send_email's own dedupe no-op) so
    the "sent" count this returns reflects only genuinely new sends
    this run, same pattern as warn_expiring_access/remind_live_session
    elsewhere in this app."""
    from apps.engagement.models import EmailLog
    from apps.engagement.services import send_email

    sent = 0
    certificates = Certificate.objects.filter(
        is_revoked=False,
        issued_at__gte=GRADUATE_MARKETING_STARTS_AT,
        enrollment__user__profile__marketing_opt_in=True,
    ).select_related("enrollment__user", "enrollment__course")

    for certificate in certificates:
        dedupe_key = f"graduate_marketing:{certificate.id}"
        if EmailLog.objects.filter(dedupe_key=dedupe_key, status=EmailLog.Status.SENT).exists():
            continue
        context = _context_for(certificate)
        html = render_to_string("emails/graduate_marketing.html", context)
        send_email(
            to_email=certificate.enrollment.user.email,
            template_key="graduate_marketing",
            subject=context["subject"],
            html=html,
            user=certificate.enrollment.user,
            dedupe_key=dedupe_key,
        )
        sent += 1
    return sent
