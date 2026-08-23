from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.catalog.models import Course
from apps.enrollment.models import Enrollment
from apps.enrollment.services import get_progress_percent

from .forms import CourseMetadataForm, InstructorApplicationForm
from .models import EarningsEntry, Instructor, Payout
from .services import get_instructor_balance, submit_course_for_review


def instructor_required(view_func):
    """Every /teach/ view (after apply/) needs a logged-in user WITH
    an Instructor row — this is the one gate all of them share."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        instructor = getattr(request.user, "instructor_profile", None)
        if instructor is None:
            messages.info(request, "You don't have an instructor account yet.")
            return redirect("instructors:apply")
        request.instructor = instructor
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def apply(request):
    existing = getattr(request.user, "instructor_profile", None)
    if existing:
        return redirect("instructors:dashboard")

    if request.method == "POST":
        form = InstructorApplicationForm(request.POST)
        if form.is_valid():
            from apps.organizations.models import Organization

            instructor = form.save(commit=False)
            instructor.user = request.user
            instructor.organization = Organization.objects.first()
            instructor.status = Instructor.Status.APPLICANT
            instructor.save()
            messages.success(request, "Application received — we'll be in touch once it's reviewed.")
            return redirect("instructors:dashboard")
    else:
        form = InstructorApplicationForm()

    return render(request, "instructors/apply.html", {"form": form})


@instructor_required
def dashboard(request):
    instructor = request.instructor
    balance_kobo = get_instructor_balance(instructor)

    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    courses = Course.objects.filter(instructor=instructor)
    enrollments_this_month = Enrollment.objects.filter(course__instructor=instructor, started_at__gte=month_start).count()
    all_enrollments = Enrollment.objects.filter(course__instructor=instructor).exclude(status=Enrollment.Status.REVOKED)
    completed = all_enrollments.filter(status=Enrollment.Status.COMPLETED).count()
    total = all_enrollments.count()
    completion_rate = round(completed * 100 / total) if total else 0

    pending_payout = Payout.objects.filter(instructor=instructor, status__in=[Payout.Status.DRAFT, Payout.Status.APPROVED]).first()

    return render(request, "instructors/dashboard.html", {
        "instructor": instructor,
        "balance_naira": balance_kobo / 100,
        "course_count": courses.count(),
        "enrollments_this_month": enrollments_this_month,
        "completion_rate": completion_rate,
        "pending_payout": pending_payout,
    })


@instructor_required
def course_list(request):
    courses = Course.objects.filter(instructor=request.instructor).order_by("-id")
    return render(request, "instructors/course_list.html", {"courses": courses})


@instructor_required
def course_edit(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.instructor)
    locked = course.review_status in (Course.ReviewStatus.SUBMITTED, Course.ReviewStatus.IN_REVIEW)

    if request.method == "POST":
        if locked:
            messages.error(request, "This course is locked for editing while it's under review.")
            return redirect("instructors:course_edit", slug=slug)
        form = CourseMetadataForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved.")
            return redirect("instructors:course_edit", slug=slug)
    else:
        form = CourseMetadataForm(instance=course)

    return render(request, "instructors/course_edit.html", {"course": course, "form": form, "locked": locked})


@require_POST
@instructor_required
def course_submit(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.instructor)
    if course.review_status not in (Course.ReviewStatus.DRAFT, Course.ReviewStatus.CHANGES_REQUESTED):
        messages.error(request, "This course isn't in a state that can be submitted.")
        return redirect("instructors:course_list")
    submit_course_for_review(course, submitted_by=request.user)
    messages.success(request, "Submitted for review.")
    return redirect("instructors:course_list")


@instructor_required
def course_learners(request, slug):
    """Names and progress ONLY — build spec §4.7 anti-poaching: never
    expose learner email or phone in /teach/. Messaging goes through
    the platform (course_messages view), not direct contact."""
    course = get_object_or_404(Course, slug=slug, instructor=request.instructor)
    enrollments = Enrollment.objects.filter(course=course).exclude(status=Enrollment.Status.REVOKED).select_related("user")
    rows = [
        {
            "name": e.user.get_full_name() or "Learner",  # deliberately never e.user.email
            "status": e.get_status_display(),
            "progress_percent": get_progress_percent(e),
        }
        for e in enrollments
    ]
    return render(request, "instructors/course_learners.html", {"course": course, "rows": rows})


@instructor_required
def earnings(request):
    entries = EarningsEntry.objects.filter(instructor=request.instructor).order_by("-created_at")[:100]
    balance_kobo = get_instructor_balance(request.instructor)
    return render(request, "instructors/earnings.html", {"entries": entries, "balance_naira": balance_kobo / 100})


@instructor_required
def marketing(request):
    from django.conf import settings
    courses = Course.objects.filter(instructor=request.instructor, is_published=True)
    links = [
        {"course": c, "url": f"{settings.SITE_URL}/courses/{c.slug}/?ref={request.instructor.referral_code}"}
        for c in courses
    ]
    return render(request, "instructors/marketing.html", {"links": links, "instructor": request.instructor})
