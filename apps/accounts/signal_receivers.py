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
    account — auto-enroll them in every published
    is_compulsory_staff_training course. This is what makes the
    'everyone's training journey starts the moment they're onboarded'
    behavior real rather than a manual step someone has to remember.
    Each person's pacing is still individual: Enrollment.started_at is
    set at creation, and DRIP_DAYS modules unlock relative to that, so
    two people onboarded weeks apart each get their own week-1/week-2/…
    schedule from their own start date."""
    if action != "post_add" or not pk_set or kwargs.get("reverse"):
        return  # reverse=True would mean `instance` is a Group, not a User — not our case here

    from apps.catalog.models import Course
    from apps.enrollment.models import Enrollment

    courses = Course.objects.filter(is_staff_training=True, is_compulsory_staff_training=True, is_published=True)
    if not courses:
        return
    for course in courses:
        Enrollment.objects.get_or_create(user=instance, course=course)


def connect():
    pass  # importing this module is enough to register the @receiver above
