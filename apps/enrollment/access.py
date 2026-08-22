"""Access control for learner-facing views — build spec §7.

One decorator guards every /learn/ view. It must check: enrollment
exists, status == ACTIVE (in real time, not just the stored field),
not past expires_at, and the requested lesson's module passes
is_module_unlocked(). Preview lessons bypass enrollment but nothing
else — no auth, no unlock check, just is_preview=True.

There must be no path where an unenrolled, non-preview visitor obtains
a playable lesson. This function is that path's only gate.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalog.models import Course, Lesson

from .models import Enrollment
from .services import is_enrollment_currently_active, is_module_unlocked


def requires_active_enrollment(view_func):
    @wraps(view_func)
    def wrapper(request, course_slug, lesson_slug=None, *args, **kwargs):
        course = get_object_or_404(Course, slug=course_slug)

        lesson = None
        module = None
        if lesson_slug:
            lesson = get_object_or_404(Lesson, slug=lesson_slug, module__course=course)
            module = lesson.module

        # Look up a real, currently-active enrollment FIRST, even for
        # a preview lesson. An actually-enrolled student must always
        # get their real progress/unlock context — is_preview is only
        # a fallback for a visitor who has none, not an override that
        # should ever discard a real enrollment. (Getting this order
        # backwards was a real bug caught in Phase 3 testing: module
        # 1's seeded lesson is marked preview, which silently broke
        # progress tracking for an enrolled learner on that lesson.)
        enrollment = None
        if request.user.is_authenticated:
            candidate = Enrollment.objects.filter(user=request.user, course=course).first()
            if candidate and is_enrollment_currently_active(candidate):
                enrollment = candidate

        if enrollment:
            if module and not is_module_unlocked(enrollment, module):
                messages.info(request, "That module isn't unlocked yet.")
                return redirect("enrollment:curriculum", course_slug=course.slug)

            request.enrollment = enrollment
            request.course = course
            request.lesson = lesson
            request.module = module
            return view_func(request, course_slug=course_slug, lesson_slug=lesson_slug, *args, **kwargs)

        # No active enrollment — anonymous, not enrolled, or enrolled
        # but expired/revoked. The only door still open is a preview
        # lesson, and only for viewing (mark-complete etc. still has
        # nothing to attach progress to, since request.enrollment is None).
        if lesson and lesson.is_preview:
            request.enrollment = None
            request.course = course
            request.lesson = lesson
            request.module = module
            return view_func(request, course_slug=course_slug, lesson_slug=lesson_slug, *args, **kwargs)

        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        response = render(request, "enrollment/no_access.html", {"course": course})
        response.status_code = 403
        return response

    return wrapper
