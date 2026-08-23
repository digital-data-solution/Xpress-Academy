"""Ensures every User always has a Profile — without this, any user
created outside SignupForm (createsuperuser, admin's "Add user" before
the ProfileInline is filled in, a future OAuth/SSO flow) would crash
the first time anything touches user.profile (checkout does, via
email_verified). Caught by testing: the very superuser created in
Phase 1 had no Profile row at all until this was added."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile, User


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


def connect():
    pass  # importing this module is enough to register the @receiver above
