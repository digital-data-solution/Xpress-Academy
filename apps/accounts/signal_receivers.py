"""Ensures every User always has a Profile — without this, any user
created outside SignupForm (createsuperuser, admin's "Add user" before
the ProfileInline is filled in, a future OAuth/SSO flow) would crash
the first time anything touches user.profile (checkout does, via
email_verified). Caught by testing: the very superuser created in
Phase 1 had no Profile row at all until this was added."""

from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .models import Profile, User


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(m2m_changed, sender=User.groups.through)
def enroll_in_compulsory_training_on_group_join(sender, instance, action, pk_set, **kwargs):
    """The moment someone is added to ANY Django Group — i.e. actually
    given a real operational role here, not just a public-learner
    account — auto-enroll them in every published, chain-HEAD
    is_compulsory_staff_training course (prerequisite is null). This
    is what makes 'everyone's training journey starts the moment
    they're onboarded' real rather than a manual step someone has to
    remember. Only chain heads enroll immediately — a course with a
    prerequisite set (e.g. course 2 of a 15-course sequence) is
    enrolled later by apps.engagement.tasks.
    advance_compulsory_training_chains_task, once its prerequisite is
    actually completed (+ unlock_delay_days), not on group-join."""
    if action != "post_add" or not pk_set or kwargs.get("reverse"):
        return  # reverse=True would mean `instance` is a Group, not a User — not our case here

    from apps.catalog.models import Course
    from apps.enrollment.models import Enrollment

    courses = Course.objects.filter(
        is_staff_training=True, is_compulsory_staff_training=True, is_published=True, prerequisite__isnull=True,
    )
    if not courses:
        return
    for course in courses:
        enrollment, was_created = Enrollment.objects.get_or_create(user=instance, course=course)
        if was_created:
            _send_welcome_to_training_email(instance, course)


def _send_welcome_to_training_email(user, course):
    """Fires immediately on group-join (not on Monday's schedule) —
    without this, a new hire's first automatic notice of their
    compulsory training would be up to 6 days late, waiting on
    apps.engagement.tasks.send_weekly_staff_training_email_task. Local
    imports: apps.engagement isn't a dependency of apps.accounts
    anywhere else, and importing at module level here would run at
    Django app-loading time, before apps.engagement's own models are
    necessarily ready. Reuses the chain_course_unlocked template and
    dedupe_key shape (chain_unlocked:<user>:<course>) — same event,
    conceptually, whether it's the first course on group-join or a
    later one via advance_compulsory_training_chains_task."""
    from django.conf import settings
    from django.template.loader import render_to_string

    from apps.engagement.services import send_email

    context = {
        "first_name": user.first_name or "there",
        "course_title": course.title, "course_slug": course.slug,
        "site_url": settings.SITE_URL,
    }
    html = render_to_string("emails/chain_course_unlocked.html", context)
    send_email(
        to_email=user.email, user=user, template_key="chain_course_unlocked",
        subject=f"Your training is ready: {course.title}", html=html,
        dedupe_key=f"chain_unlocked:{user.id}:{course.id}",
    )


def connect():
    pass  # importing this module is enough to register the @receiver above
