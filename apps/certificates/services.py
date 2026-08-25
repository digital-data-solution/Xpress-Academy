"""Certificate issuance — build spec §8 Phase 5: "Completion rule
service, PDF generation, serial + verification slug ... only when the
enrollment meets the completion rule."

Generation is triggered inline at the moment an enrollment completes
(called from apps.enrollment.services._mark_enrollment_completed_if_ready)
rather than by a Celery task — the spec says "triggered by a Celery
task," but by the time Phase 7 actually wired Celery, there was no
reason to move this off the inline call: it's event-triggered, not
scheduled, so there's nothing for a beat schedule to do here. It stays
synchronous. issue_certificate() is also callable directly from admin
for a manual/backfill case.
"""

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Audience
from apps.enrollment.services import is_course_complete

from .models import Certificate, CertificateSequence
from .pdf import build_certificate_pdf

AUDIENCE_CODES = {
    Audience.BREEDER: "BRD",
    Audience.VET: "VET",
    Audience.GENERAL: "GEN",
}


def next_serial(course) -> str:
    year = timezone.now().year
    code = AUDIENCE_CODES.get(course.audience, "GEN")
    with transaction.atomic():
        seq, _ = CertificateSequence.objects.select_for_update().get_or_create(
            audience_code=code, year=year
        )
        seq.last_number += 1
        seq.save(update_fields=["last_number"])
        return f"XDA-{code}-{year}-{seq.last_number:05d}"


@transaction.atomic
def issue_certificate(enrollment, *, bypass_payment_gate=False):
    """Idempotent — returns the existing Certificate if one already
    exists for this enrollment. Returns None (issues nothing) if the
    completion rule isn't actually met, so it's always safe to call
    speculatively — including the automatic call from
    _mark_enrollment_completed_if_ready every time a course completes.

    bypass_payment_gate=True is passed only from
    apps.payments.services.grant_access, after a successful
    Payment.Purpose.CERTIFICATE payment — that's the only legitimate
    way past the gate below for a CERTIFICATE_PAID course. The
    automatic on-completion call always passes False, so a
    CERTIFICATE_PAID course's certificate simply doesn't exist yet
    until it's paid for; completing the course itself stays free."""
    existing = Certificate.objects.filter(enrollment=enrollment).first()
    if existing:
        return existing

    if not is_course_complete(enrollment):
        return None

    course = enrollment.course
    if course.pricing_model == course.PricingModel.CERTIFICATE_PAID and not bypass_payment_gate:
        return None

    final_score = None
    if course.requires_final_assessment:
        from apps.assessment.models import Attempt, Quiz

        final_quiz = Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).first()
        if final_quiz:
            best = (
                Attempt.objects.filter(enrollment=enrollment, quiz=final_quiz, passed=True)
                .order_by("-score_percent")
                .first()
            )
            final_score = best.score_percent if best else None

    certificate = Certificate.objects.create(
        enrollment=enrollment,
        serial=next_serial(course),
        learner_name_snapshot=(enrollment.user.get_full_name() or enrollment.user.email),
        course_title_snapshot=course.title,
        final_score=final_score,
    )

    pdf_bytes = build_certificate_pdf(certificate)
    from django.core.files.base import ContentFile

    certificate.pdf.save(f"{certificate.serial}.pdf", ContentFile(pdf_bytes), save=True)

    def _send_certificate_email():
        from apps.engagement.services import send_certificate_issued_email
        send_certificate_issued_email(certificate)

    transaction.on_commit(_send_certificate_email)

    return certificate


def revoke_certificate(certificate: Certificate, reason: str) -> Certificate:
    certificate.is_revoked = True
    certificate.revoked_reason = reason
    certificate.revoked_at = timezone.now()
    certificate.save(update_fields=["is_revoked", "revoked_reason", "revoked_at"])
    return certificate
