"""Certificate PDF rendering — ReportLab, not WeasyPrint.

Deviation from build spec §8 ("WeasyPrint or ReportLab"): WeasyPrint
needs Pango/Cairo/GDK-Pixbuf system libraries that are genuinely
painful to install on native Windows (this is a Windows dev machine —
see README). ReportLab is pure Python, installs cleanly via pip, no
system dependency. Both were named as acceptable in the spec.

The wording below is exact per build spec §4 and must never be
softened or "improved" — it is a completion certificate, not a
regulatory credential, and the forbidden-words check in
apps.certificates.tests exists specifically to catch a future edit
that adds one back in.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# DO NOT EDIT this wording without updating build-spec §4 first, and
# DO NOT add "accredited", "licensed", "approved", "VCN", or "TRCN"
# anywhere on the certificate — see apps.certificates.tests.
CERTIFICATE_WORDING = (
    "Certificate of Completion — issued by Xpress Digital Academy, "
    "a brand of Xpress Digital & Data Solutions Limited (RC 9112280)."
)

FORBIDDEN_WORDS = ["accredited", "licensed", "approved", "VCN", "TRCN"]


def build_certificate_pdf(certificate) -> bytes:
    """Renders the certificate to PDF bytes. Does not save the file —
    callers attach it to certificate.pdf themselves (see
    services.issue_certificate)."""
    buffer = io.BytesIO()
    page_size = landscape(A4)
    width, height = page_size
    c = canvas.Canvas(buffer, pagesize=page_size)

    # Border
    c.setStrokeColor(colors.HexColor("#166534"))
    c.setLineWidth(3)
    c.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)

    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(colors.HexColor("#166534"))
    c.drawCentredString(width / 2, height - 4 * cm, "Certificate of Completion")

    c.setFont("Helvetica", 13)
    c.setFillColor(colors.black)
    c.drawCentredString(width / 2, height - 5.5 * cm, "This certifies that")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 7 * cm, certificate.learner_name_snapshot)

    c.setFont("Helvetica", 13)
    c.drawCentredString(width / 2, height - 8.3 * cm, "has completed")

    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 9.6 * cm, certificate.course_title_snapshot)

    if certificate.final_score is not None:
        c.setFont("Helvetica", 12)
        c.drawCentredString(width / 2, height - 10.8 * cm, f"Final score: {certificate.final_score}%")

    # Required wording, verbatim — see module docstring.
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawCentredString(width / 2, 3.6 * cm, CERTIFICATE_WORDING)

    # Serial / date, bottom-left; signature, bottom-right
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(2.2 * cm, 2.4 * cm, f"Serial: {certificate.serial}")
    c.drawString(2.2 * cm, 1.9 * cm, f"Issued: {certificate.issued_at.strftime('%d %B %Y')}")
    c.drawString(2.2 * cm, 1.4 * cm, f"Verify: /verify/{certificate.verification_slug}/")

    org = certificate.enrollment.course.organization
    if org.certificate_signatory_name:
        c.setFont("Helvetica-Bold", 11)
        c.drawRightString(width - 2.2 * cm, 2.4 * cm, org.certificate_signatory_name)
        if org.certificate_signatory_title:
            c.setFont("Helvetica", 9)
            c.drawRightString(width - 2.2 * cm, 1.9 * cm, org.certificate_signatory_title)

    c.showPage()
    c.save()
    return buffer.getvalue()
