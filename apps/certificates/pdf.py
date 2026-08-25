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


PRIMARY = colors.HexColor("#166534")
PRIMARY_DARK = colors.HexColor("#113f24")
PRIMARY_SOFT = colors.HexColor("#ecfdf5")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6b7280")


def _draw_corner_flourish(c, x, y, dx, dy, size=1.1 * cm):
    """One elegant double-line corner mark, mirrored via dx/dy = ±1
    for whichever of the four corners this call is for. Purely
    decorative — the kind of detail that's the actual difference
    between "a bordered rectangle" and "a certificate.\""""
    c.setStrokeColor(PRIMARY)
    c.setLineWidth(1.6)
    c.line(x, y, x + dx * size, y)
    c.line(x, y, x, y + dy * size)
    c.setLineWidth(0.6)
    inset = 0.22 * cm
    c.line(x + dx * inset, y + dy * inset, x + dx * (size - inset), y + dy * inset)
    c.line(x + dx * inset, y + dy * inset, x + dx * inset, y + dy * (size - inset))


def build_certificate_pdf(certificate) -> bytes:
    """Renders the certificate to PDF bytes. Does not save the file —
    callers attach it to certificate.pdf themselves (see
    services.issue_certificate)."""
    buffer = io.BytesIO()
    page_size = landscape(A4)
    width, height = page_size
    c = canvas.Canvas(buffer, pagesize=page_size)
    cx = width / 2

    # Full-bleed very light tint, then the actual certificate frame
    # inset from the page edge — the two-border look matches the
    # site's own certificate page (.cert-frame in app.css), so a
    # downloaded PDF and the on-site view read as the same object.
    c.setFillColor(PRIMARY_SOFT)
    c.rect(0, 0, width, height, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.rect(0.9 * cm, 0.9 * cm, width - 1.8 * cm, height - 1.8 * cm, stroke=0, fill=1)

    # Double border
    c.setStrokeColor(PRIMARY)
    c.setLineWidth(2.4)
    c.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)
    c.setLineWidth(0.7)
    c.rect(1.55 * cm, 1.55 * cm, width - 3.1 * cm, height - 3.1 * cm)

    # Corner flourishes, all four, mirrored
    m = 1.85 * cm
    _draw_corner_flourish(c, m, height - m, 1, -1)
    _draw_corner_flourish(c, width - m, height - m, -1, -1)
    _draw_corner_flourish(c, m, m, 1, 1)
    _draw_corner_flourish(c, width - m, m, -1, 1)

    # Seal — a plain circular badge with a checkmark, same visual
    # language as the "XA" logo mark and the cert-seal element on the
    # site's own certificate page, not a photo/graphic asset.
    seal_r = 1.15 * cm
    seal_cy = height - 3.15 * cm
    c.setFillColor(PRIMARY)
    c.circle(cx, seal_cy, seal_r, stroke=0, fill=1)
    c.setStrokeColor(colors.white)
    c.setLineWidth(2.6)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(cx - 0.42 * cm, seal_cy - 0.02 * cm)
    p.lineTo(cx - 0.12 * cm, seal_cy - 0.32 * cm)
    p.lineTo(cx + 0.42 * cm, seal_cy + 0.32 * cm)
    c.drawPath(p, stroke=1, fill=0)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, height - 4.55 * cm, "XPRESS DIGITAL ACADEMY")

    c.setFont("Times-Bold", 30)
    c.setFillColor(PRIMARY)
    c.drawCentredString(cx, height - 5.55 * cm, "Certificate of Completion")

    c.setFont("Helvetica", 13)
    c.setFillColor(INK)
    c.drawCentredString(cx, height - 7.0 * cm, "This certifies that")

    c.setFont("Times-Bold", 25)
    c.setFillColor(INK)
    c.drawCentredString(cx, height - 8.35 * cm, certificate.learner_name_snapshot)

    # Short rule under the learner's name — a classic certificate
    # convention, drawn rather than needing any asset.
    name_width = c.stringWidth(certificate.learner_name_snapshot, "Times-Bold", 25)
    rule_half = min(max(name_width / 2, 3 * cm), 9 * cm)
    c.setStrokeColor(PRIMARY)
    c.setLineWidth(1)
    c.line(cx - rule_half, height - 8.75 * cm, cx + rule_half, height - 8.75 * cm)

    c.setFont("Helvetica", 13)
    c.setFillColor(INK)
    c.drawCentredString(cx, height - 9.7 * cm, "has completed")

    c.setFont("Times-Bold", 19)
    c.setFillColor(PRIMARY_DARK)
    c.drawCentredString(cx, height - 10.9 * cm, certificate.course_title_snapshot)

    if certificate.final_score is not None:
        c.setFont("Helvetica", 12)
        c.setFillColor(MUTED)
        c.drawCentredString(cx, height - 11.95 * cm, f"Final score: {certificate.final_score}%")

    # Required wording, verbatim — see module docstring.
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, 3.5 * cm, CERTIFICATE_WORDING)

    # A thin rule separates the formal wording/meta footer from the
    # certificate body above it.
    c.setStrokeColor(colors.HexColor("#d1d5db"))
    c.setLineWidth(0.5)
    c.line(2.4 * cm, 3.95 * cm, width - 2.4 * cm, 3.95 * cm)

    # Serial / date / verify, bottom-left; signature, bottom-right
    c.setFont("Helvetica", 9)
    c.setFillColor(INK)
    c.drawString(2.2 * cm, 2.6 * cm, f"Serial: {certificate.serial}")
    c.drawString(2.2 * cm, 2.15 * cm, f"Issued: {certificate.issued_at.strftime('%d %B %Y')}")
    c.drawString(2.2 * cm, 1.7 * cm, f"Verify: /verify/{certificate.verification_slug}/")

    org = certificate.enrollment.course.organization
    if org.certificate_signatory_name:
        sig_x = width - 2.2 * cm
        c.setStrokeColor(colors.HexColor("#9ca3af"))
        c.setLineWidth(0.6)
        c.line(sig_x - 5 * cm, 2.85 * cm, sig_x, 2.85 * cm)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(INK)
        c.drawRightString(sig_x, 2.5 * cm, org.certificate_signatory_name)
        if org.certificate_signatory_title:
            c.setFont("Helvetica", 9)
            c.setFillColor(MUTED)
            c.drawRightString(sig_x, 2.1 * cm, org.certificate_signatory_title)

    c.showPage()
    c.save()
    return buffer.getvalue()
