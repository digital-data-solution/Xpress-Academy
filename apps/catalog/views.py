from django.shortcuts import get_object_or_404, render

from apps.organizations.models import Organization

from .models import Course


def landing(request):
    org = Organization.objects.filter(is_active=True).first()
    featured_courses = Course.objects.filter(is_published=True).select_related("programme")[:6]
    return render(request, "catalog/landing.html", {"org": org, "featured_courses": featured_courses})


def course_catalog(request):
    courses = Course.objects.filter(is_published=True).select_related("programme").order_by("title")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        courses = courses.filter(Q(title__icontains=query) | Q(subtitle__icontains=query))
    return render(request, "catalog/course_catalog.html", {"courses": courses, "query": query})


def course_detail(request, slug):
    course = get_object_or_404(Course, slug=slug, is_published=True)
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
