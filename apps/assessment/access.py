"""Access control for quiz views — same discipline as
apps.enrollment.access.requires_active_enrollment (build spec §7),
adapted for a quiz instead of a lesson. A MODULE-scope quiz also
requires its module to be unlocked; a FINAL-scope quiz just needs an
active enrollment (attempting the final assessment isn't itself
locked behind lesson completion — only *passing* course completion is,
via is_course_complete)."""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.catalog.models import Course
from apps.enrollment.models import Enrollment
from apps.enrollment.services import is_enrollment_currently_active, is_module_unlocked

from .models import Quiz


def requires_quiz_access(view_func):
    @wraps(view_func)
    def wrapper(request, course_slug, quiz_id, *args, **kwargs):
        course = get_object_or_404(Course, slug=course_slug)
        quiz = get_object_or_404(Quiz, pk=quiz_id)
        if quiz.course_ref.id != course.id:
            raise Http404("Quiz does not belong to this course.")

        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        enrollment = Enrollment.objects.filter(user=request.user, course=course).first()
        if not enrollment or not is_enrollment_currently_active(enrollment):
            response = render(request, "enrollment/no_access.html", {"course": course})
            response.status_code = 403
            return response

        if quiz.scope == Quiz.Scope.MODULE and not is_module_unlocked(enrollment, quiz.module):
            messages.info(request, "That module isn't unlocked yet.")
            return redirect("enrollment:curriculum", course_slug=course.slug)

        request.course = course
        request.quiz = quiz
        request.enrollment = enrollment
        return view_func(request, course_slug=course_slug, quiz_id=quiz_id, *args, **kwargs)

    return wrapper
