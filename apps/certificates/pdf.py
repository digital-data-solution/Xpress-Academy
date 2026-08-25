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

from django.conf import settings
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.common.models import CertificateSignatureMode

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


def _draw_corner_flourish(c, x, y, dx, dy, size=0.85 * cm):
    """One elegant double-line corner mark, mirrored via dx/dy = ±1
    for whichever of the four corners this call is for. Purely
    decorative — the kind of detail that's the actual difference
    between "a bordered rectangle" and "a certificate."

    size was 1.1cm and the marks sat at 1.85cm from the edge — close
    enough to the footer text block (which starts at 2.2cm) that they
    visually collided with the serial/signature lines on a real
    render. Shrunk and moved fractionally closer to the true corner
    so the mark stays inside the border framing, never reaching text."""
    c.setStrokeColor(PRIMARY)
    c.setLineWidth(1.4)
    c.line(x, y, x + dx * size, y)
    c.line(x, y, x, y + dy * size)
    c.setLineWidth(0.5)
    inset = 0.18 * cm
    c.line(x + dx * inset, y + dy * inset, x + dx * (size - inset), y + dy * inset)
    c.line(x + dx * inset, y + dy * inset, x + dx * inset, y + dy * (size - inset))


WATERMARK_FILL = colors.HexColor("#ecf3ef")   # ~8% PRIMARY mixed into white
WATERMARK_STROKE = colors.HexColor("#cfe2d6")  # ~20% PRIMARY mixed into white


def _draw_watermark(c, cx, cy):
    """A large, faint ghost of the seal centered behind the
    certificate body — the classic "security paper" cue that makes a
    document read as harder to casually forge, and also gives the
    previously-empty middle of the page something to hold visually
    instead of dead space.

    Plain light colors, not real alpha transparency — tried
    setFillAlpha/setStrokeAlpha first and confirmed via a rendered
    test PDF that this reportlab/viewer combination does NOT actually
    apply the transparency (came out fully opaque, not faint), so
    trusting alpha here would have shipped a watermark that hides the
    whole certificate behind a solid green disc. Precomputed
    light-mix hex colors render identically everywhere, no
    transparency compositing to trust."""
    r = 5.4 * cm
    c.setFillColor(WATERMARK_FILL)
    c.circle(cx, cy, r, stroke=0, fill=1)
    c.setStrokeColor(WATERMARK_STROKE)
    c.setLineWidth(10)
    c.setLineCap(1)
    p = c.beginPath()
    p.moveTo(cx - 1.9 * cm, cy - 0.1 * cm)
    p.lineTo(cx - 0.55 * cm, cy - 1.45 * cm)
    p.lineTo(cx + 1.9 * cm, cy + 1.45 * cm)
    c.drawPath(p, stroke=1, fill=0)


def _resolve_signature(*, signer, fallback_name, default_title, org_name):
    """signer is whichever party actually signs this certificate — an
    Instructor for their own course, or the Organization for a
    first-party one. Both models carry the same four fields (see
    CertificateSignatureMode's docstring for why the mode is explicit
    rather than inferred), so this one function handles either.

    Returns a dict the caller draws directly: {"style": "image"|"name"|"plain", ...}
    - "image": an uploaded signature image, drawn above the printed name/title
    - "name": the classic rule-line + bold name + title
    - "plain": just the organization's name, no rule, no implied
      personal signature — for someone who deliberately doesn't want
      their own name on a certificate (a real, explicit choice, not a
      fallback for "forgot to fill in a name")
    """
    mode = signer.certificate_signature_mode
    if mode == CertificateSignatureMode.ORG_NAME_ONLY:
        return {"style": "plain", "name": org_name}

    name = signer.certificate_signatory_name or fallback_name
    title = signer.certificate_signatory_title or default_title

    if mode == CertificateSignatureMode.SIGNATURE_IMAGE and signer.certificate_signature_image:
        return {"style": "image", "image": signer.certificate_signature_image, "name": name, "title": title}

    # NAME_TITLE, or SIGNATURE_IMAGE chosen but nothing's actually
    # been uploaded yet — fall back to the name/title style rather
    # than drawing nothing.
    return {"style": "name", "name": name, "title": title}


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

    # Watermark first — everything else draws on top of it.
    _draw_watermark(c, cx, height / 2)

    # Double border
    c.setStrokeColor(PRIMARY)
    c.setLineWidth(2.4)
    c.rect(1.2 * cm, 1.2 * cm, width - 2.4 * cm, height - 2.4 * cm)
    c.setLineWidth(0.7)
    c.rect(1.55 * cm, 1.55 * cm, width - 3.1 * cm, height - 3.1 * cm)

    # Corner flourishes, all four, mirrored — kept close to the true
    # corner (see _draw_corner_flourish's docstring for why this
    # margin matters) so they never reach the footer text.
    m = 1.55 * cm
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

    # A real, scannable QR code linking straight to the public
    # verification page — the previously-empty middle of the
    # certificate now does double duty: fills the dead space AND is
    # the actual "prove this is authentic" feature, not just
    # decorative. reportlab.graphics.barcode ships with reportlab
    # itself, no extra dependency.
    verify_url = f"{settings.SITE_URL.rstrip('/')}/verify/{certificate.verification_slug}/"
    qr_code = qr.QrCodeWidget(verify_url)
    qr_bounds = qr_code.getBounds()
    qr_native_w = qr_bounds[2] - qr_bounds[0]
    qr_native_h = qr_bounds[3] - qr_bounds[1]
    qr_size = 2.6 * cm
    qr_y = height - 15.6 * cm
    drawing = Drawing(qr_size, qr_size, transform=[qr_size / qr_native_w, 0, 0, qr_size / qr_native_h, 0, 0])
    drawing.add(qr_code)
    renderPDF.draw(drawing, c, cx - qr_size / 2, qr_y)

    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, qr_y - 0.4 * cm, "Scan to verify authenticity")

    # Required wording, verbatim — see module docstring.
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED)
    c.drawCentredString(cx, 3.5 * cm, CERTIFICATE_WORDING)

    # A thin rule separates the formal wording/meta footer from the
    # certificate body above it.
    c.setStrokeColor(colors.HexColor("#d1d5db"))
    c.setLineWidth(0.5)
    c.line(2.4 * cm, 3.95 * cm, width - 2.4 * cm, 3.95 * cm)

    # Serial / date, bottom-left (the QR code above already covers
    # "verify" better than a typed URL ever did); signature, bottom-right.
    c.setFont("Helvetica", 9)
    c.setFillColor(INK)
    c.drawString(2.2 * cm, 2.5 * cm, f"Serial: {certificate.serial}")
    c.drawString(2.2 * cm, 2.05 * cm, f"Issued: {certificate.issued_at.strftime('%d %B %Y')}")

    # Who signs depends on who actually taught the course: a
    # marketplace instructor's own course is signed by that
    # instructor (their expertise, their credibility — same as how
    # Udemy/similar platforms attribute a course's certificate), not
    # the org founder. instructor_id is null only for first-party
    # Xpress-authored courses, which fall back to the org's own
    # configured signatory. Each party's own certificate_signature_mode
    # decides HOW they're represented — see _resolve_signature.
    course = certificate.enrollment.course
    org = course.organization
    if course.instructor_id:
        signature = _resolve_signature(
            signer=course.instructor, fallback_name=course.instructor.display_name,
            default_title="Instructor", org_name=org.name,
        )
    else:
        signature = _resolve_signature(
            signer=org, fallback_name=org.name, default_title="", org_name=org.name,
        )

    sig_x = width - 2.2 * cm

    if signature["style"] == "plain":
        # Deliberately no rule line and no bold name — this isn't a
        # person's signature, it's a plain "issued by" credit.
        c.setFont("Helvetica", 10)
        c.setFillColor(MUTED)
        c.drawRightString(sig_x, 2.3 * cm, f"Issued by {signature['name']}")

    elif signature["style"] == "image":
        try:
            signature["image"].open("rb")
            image_bytes = signature["image"].read()
        finally:
            signature["image"].close()
        img_reader = ImageReader(io.BytesIO(image_bytes))
        native_w, native_h = img_reader.getSize()
        max_h, max_w = 1.3 * cm, 4.2 * cm
        scale = min(max_h / native_h, max_w / native_w)
        img_w, img_h = native_w * scale, native_h * scale
        c.drawImage(
            img_reader, sig_x - img_w, 2.95 * cm, width=img_w, height=img_h,
            preserveAspectRatio=True, mask="auto",
        )
        c.setStrokeColor(colors.HexColor("#9ca3af"))
        c.setLineWidth(0.6)
        c.line(sig_x - 5 * cm, 2.85 * cm, sig_x, 2.85 * cm)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(INK)
        c.drawRightString(sig_x, 2.5 * cm, signature["name"])
        if signature["title"]:
            c.setFont("Helvetica", 9)
            c.setFillColor(MUTED)
            c.drawRightString(sig_x, 2.1 * cm, signature["title"])

    elif signature["style"] == "name" and signature["name"]:
        c.setStrokeColor(colors.HexColor("#9ca3af"))
        c.setLineWidth(0.6)
        c.line(sig_x - 5 * cm, 2.85 * cm, sig_x, 2.85 * cm)
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(INK)
        c.drawRightString(sig_x, 2.5 * cm, signature["name"])
        if signature["title"]:
            c.setFont("Helvetica", 9)
            c.setFillColor(MUTED)
            c.drawRightString(sig_x, 2.1 * cm, signature["title"])

    c.showPage()
    c.save()
    return buffer.getvalue()
