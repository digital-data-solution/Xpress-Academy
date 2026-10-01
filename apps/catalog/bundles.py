"""Courses that come with each other: buying (or being freely enrolled
in) the key course also enrolls the learner in every listed course.

A plain slug map rather than a Course M2M field on purpose: production
deploys don't run `migrate` (see render.yaml's buildCommand), so a
schema change would break every Course query until someone ran it by
hand. This map ships safely on a normal push.

Why the PSR pair exists: the exam prep is a 40-question bank with no
lessons, and a paying student (2026-09-22) bought it expecting the
narrated chapters — it read as a scam. Either one now grants both.
"""
from .models import Course

INCLUDED_COURSE_SLUGS = {
    "civil-service-psr-exam-prep": ["public-service-rules-guide"],
    "public-service-rules-guide": ["civil-service-psr-exam-prep"],
}


def get_included_courses(course):
    """Published courses that come free with `course`. One level only —
    never follows the included courses' own entries, so a two-way pair
    can't loop."""
    slugs = INCLUDED_COURSE_SLUGS.get(course.slug, [])
    if not slugs:
        return Course.objects.none()
    return Course.objects.filter(slug__in=slugs, is_published=True).order_by("title")
