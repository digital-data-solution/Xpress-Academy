"""Growth dashboard — an honest, in-house "picture of growth" built
from data already in this database, not a third-party analytics
service. No new vendor, no visitor tracking/cookies to disclose, no
API key to manage — deliberately, same reasoning as everywhere else in
this codebase that a DIY answer already covers the need (see e.g. the
SVG certificate generation instead of a paid template service).
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

CHART_WIDTH = 600
CHART_HEIGHT = 120
CHART_PAD = 8


def _daily_counts(queryset, date_field, date_list, start):
    rows = (
        queryset.filter(**{f"{date_field}__date__gte": start})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(n=Count("id"))
    )
    by_day = {r["day"]: r["n"] for r in rows}
    return [by_day.get(d, 0) for d in date_list]


def _daily_sum(queryset, date_field, amount_field, date_list, start):
    rows = (
        queryset.filter(**{f"{date_field}__date__gte": start})
        .annotate(day=TruncDate(date_field))
        .values("day")
        .annotate(n=Sum(amount_field))
    )
    by_day = {r["day"]: (r["n"] or 0) for r in rows}
    return [by_day.get(d, 0) for d in date_list]


def _svg_points(values):
    """Points for an SVG <polyline>, normalized into a fixed
    CHART_WIDTH x CHART_HEIGHT viewBox — no charting library, just
    plain geometry, same self-contained spirit as the rest of this
    codebase's graphics (certificate PDFs, the OG image)."""
    n = len(values)
    if n <= 1:
        return "", 0
    vmax = max(values) or 1
    usable_h = CHART_HEIGHT - 2 * CHART_PAD
    step = CHART_WIDTH / (n - 1)
    points = []
    for i, v in enumerate(values):
        x = i * step
        y = CHART_HEIGHT - CHART_PAD - (v / vmax) * usable_h
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points), vmax


def build_growth_context(organization, days=30) -> dict:
    from apps.accounts.models import User
    from apps.catalog.models import Course
    from apps.certificates.models import Certificate
    from apps.enrollment.models import Enrollment
    from apps.instructors.models import Instructor
    from apps.payments.models import Payment

    today = timezone.now().date()
    start = today - timedelta(days=days - 1)
    date_list = [start + timedelta(n) for n in range(days)]

    signups = _daily_counts(User.objects.all(), "date_joined", date_list, start)
    enrollments = _daily_counts(Enrollment.objects.all(), "started_at", date_list, start)
    completions = _daily_counts(
        Enrollment.objects.filter(status=Enrollment.Status.COMPLETED), "completed_at", date_list, start
    )
    certificates = _daily_counts(
        Certificate.objects.filter(is_revoked=False), "issued_at", date_list, start
    )
    revenue_kobo = _daily_sum(
        Payment.objects.filter(status=Payment.Status.SUCCESS), "paid_at", "amount_kobo", date_list, start
    )
    revenue_naira = [k / 100 for k in revenue_kobo]

    metrics = []
    for key, label, values, fmt in [
        ("signups", "New sign-ups", signups, "int"),
        ("enrollments", "New enrollments", enrollments, "int"),
        ("completions", "Course completions", completions, "int"),
        ("certificates", "Certificates issued", certificates, "int"),
        ("revenue", "Revenue (₦/day)", revenue_naira, "naira"),
    ]:
        points, vmax = _svg_points(values)
        metrics.append({
            "key": key, "label": label, "points": points, "max": vmax,
            "total": sum(values), "fmt": fmt,
            "period_total_display": f"₦{sum(values):,.0f}" if fmt == "naira" else f"{sum(values):,}",
        })

    total_revenue_kobo = Payment.objects.filter(status=Payment.Status.SUCCESS).aggregate(s=Sum("amount_kobo"))["s"] or 0

    totals = {
        "total_learners": User.objects.filter(is_staff=False).count(),
        "total_enrollments": Enrollment.objects.count(),
        "total_completions": Enrollment.objects.filter(status=Enrollment.Status.COMPLETED).count(),
        "total_certificates": Certificate.objects.filter(is_revoked=False).count(),
        "total_revenue_naira": total_revenue_kobo / 100,
        "published_courses": Course.objects.filter(is_published=True).count(),
        "verified_instructors": Instructor.objects.filter(
            verification_status=Instructor.VerificationStatus.VERIFIED
        ).count(),
    }

    return {
        "days": days,
        "totals": totals,
        "metrics": metrics,
        "chart_width": CHART_WIDTH,
        "chart_height": CHART_HEIGHT,
        "range_start": start,
        "range_end": today,
    }
