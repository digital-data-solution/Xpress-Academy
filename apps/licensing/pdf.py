"""Diagnostic report PDFs — build spec §B: "Make it shareable as a
PDF." Uses reportlab.platypus (table/paragraph flow layout), not the
raw-canvas style apps.certificates.pdf uses — that file draws one
fixed, highly art-directed certificate layout by hand; these are
data-driven tabular reports of variable length (a school summary has
one row per student), which is exactly what platypus's flowables are
for. Same library choice as certificates (ReportLab, not WeasyPrint —
see that module's docstring for why), just the other half of it.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

styles = getSampleStyleSheet()


def _topic_table(topic_breakdown: dict) -> Table:
    rows = [["Topic", "Score"]]
    for topic, stats in sorted(topic_breakdown.items()):
        total = stats.get("total", 0) or 1
        pct = round(stats.get("correct", 0) * 100 / total)
        rows.append([topic, f"{stats.get('correct', 0)}/{stats.get('total', 0)} ({pct}%)"])

    table = Table(rows, colWidths=[10 * cm, 6 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A2E5C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def build_diagnostic_report_pdf(attempt) -> bytes:
    """One student's own report — the per-student half of build spec
    §B's diagnostic deliverable."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = []

    story.append(Paragraph("Xpress Digital Academy — Diagnostic Report", styles["Title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(attempt.test.title, styles["Heading2"]))
    story.append(Spacer(1, 0.4 * cm))

    meta = (
        f"<b>Student:</b> {attempt.student_name}"
        + (f" &nbsp;&nbsp; <b>School:</b> {attempt.school_name}" if attempt.school_name else "")
        + f"<br/><b>Date:</b> {attempt.submitted_at:%d %B %Y}"
    )
    story.append(Paragraph(meta, styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph(f"Overall score: {attempt.score_percent}%", styles["Heading1"]))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Breakdown by topic", styles["Heading3"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_topic_table(attempt.topic_breakdown))
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph(
        "This is a free diagnostic to show where to focus revision. "
        "Xpress Digital Academy offers full JAMB prep coverage for schools — "
        "ask about institutional licensing.",
        styles["Italic"],
    ))

    doc.build(story)
    return buffer.getvalue()


def build_school_summary_pdf(test, attempts) -> bytes:
    """The school-level rollup a proprietor can show parents — build
    spec §B: "a school-level summary... Make it shareable as a PDF."
    `attempts` is whatever queryset/list the caller has already scoped
    (by test.institution, by self-reported school_name, or the whole
    test) — this function only renders it."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = []

    story.append(Paragraph("Xpress Digital Academy — Diagnostic Summary", styles["Title"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(test.title, styles["Heading2"]))
    story.append(Spacer(1, 0.4 * cm))

    attempts = list(attempts)
    if not attempts:
        story.append(Paragraph("No completed attempts yet.", styles["Normal"]))
        doc.build(story)
        return buffer.getvalue()

    avg = round(sum(a.score_percent for a in attempts) / len(attempts))
    story.append(Paragraph(
        f"{len(attempts)} student{'s' if len(attempts) != 1 else ''} completed this diagnostic — average score {avg}%.",
        styles["Normal"],
    ))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Per-student results", styles["Heading3"]))
    story.append(Spacer(1, 0.2 * cm))
    rows = [["Student", "Score", "Date"]]
    for a in sorted(attempts, key=lambda a: -a.score_percent):
        rows.append([a.student_name, f"{a.score_percent}%", a.submitted_at.strftime("%d %b %Y")])
    student_table = Table(rows, colWidths=[8 * cm, 3 * cm, 5 * cm])
    student_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A2E5C")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 0.6 * cm))

    # Cohort-level topic rollup — sum correct/total across every
    # attempt's own topic_breakdown rather than re-deriving from the
    # bank, same snapshot-is-authoritative discipline as everywhere
    # else in this pipeline.
    cohort_topics: dict[str, dict[str, int]] = {}
    for a in attempts:
        for topic, stats in (a.topic_breakdown or {}).items():
            bucket = cohort_topics.setdefault(topic, {"correct": 0, "total": 0})
            bucket["correct"] += stats.get("correct", 0)
            bucket["total"] += stats.get("total", 0)

    story.append(Paragraph("Cohort-wide weak spots", styles["Heading3"]))
    story.append(Spacer(1, 0.2 * cm))
    story.append(_topic_table(cohort_topics))

    doc.build(story)
    return buffer.getvalue()
