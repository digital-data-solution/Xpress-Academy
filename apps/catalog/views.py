from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.organizations.models import Organization

from .models import Course


def landing(request):
    org = Organization.objects.filter(is_active=True).first()
    featured_courses = Course.objects.filter(
        is_published=True, is_staff_training=False
    ).select_related("programme")[:6]
    return render(request, "catalog/landing.html", {"org": org, "featured_courses": featured_courses})


def course_catalog(request):
    # Staff-training courses never appear in the public catalog, no
    # matter who's viewing it — they're reached only through
    # /staff/training/, which is itself staff-only. See course_detail
    # below for the matching gate on the detail page.
    courses = Course.objects.filter(
        is_published=True, is_staff_training=False
    ).select_related("programme").order_by("title")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        courses = courses.filter(Q(title__icontains=query) | Q(subtitle__icontains=query))
    return render(request, "catalog/course_catalog.html", {"courses": courses, "query": query})


@login_required
def staff_training_list(request):
    """The internal-training menu — /staff/training/. Deliberately NOT
    gated on is_staff (Django-admin login rights) — someone at the
    parent organization who needs training here may have no reason to
    ever touch the Academy's admin. Access is per-course, via
    Enrollment: a superuser sees every published training course (an
    oversight view — see who's assigned what), everyone else sees only
    courses they're already enrolled in (enrolled by an admin, in the
    Enrollment admin — see course_detail below for the matching gate)."""
    courses = Course.objects.filter(is_published=True, is_staff_training=True).select_related("programme")
    if not request.user.is_superuser:
        courses = courses.filter(enrollments__user=request.user)
    return render(request, "catalog/staff_training_list.html", {"courses": courses.distinct().order_by("title")})


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
    if course.is_staff_training:
        # Not is_staff (Django-admin login) — access is per-course, via
        # Enrollment, so someone can be granted training without ever
        # getting admin rights. A superuser can always preview.
        allowed = request.user.is_authenticated and (
            request.user.is_superuser
            or request.user.enrollments.filter(course=course).exists()
        )
        if not allowed:
            # Pretend it doesn't exist rather than 403 — don't even
            # confirm to an unauthorized visitor that an internal
            # training course with this slug exists.
            from django.http import Http404
            raise Http404
    modules = course.modules.order_by("order").prefetch_related("lessons")
    faqs = course.faqs.order_by("order")

    is_enrolled = False
    prerequisite_met = True
    if request.user.is_authenticated:
        is_enrolled = request.user.enrollments.filter(
            course=course, status__in=["ACTIVE", "COMPLETED"]
        ).exists()
        if course.prerequisite_id:
            prerequisite_met = request.user.enrollments.filter(
                course=course.prerequisite, status="COMPLETED"
            ).exists()

    return render(request, "catalog/course_detail.html", {
        "course": course, "modules": modules, "faqs": faqs, "is_enrolled": is_enrolled,
        "prerequisite_met": prerequisite_met,
    })
