from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    """Custom user model — email as the login identifier, no username.

    This must exist before the first migration ever runs (Django cannot
    swap AUTH_USER_MODEL later without a painful rebuild). Auth here is
    Django's own session auth. This is a separate product with its own
    user base — do NOT wire Supabase Auth into this app.
    """

    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class Profile(models.Model):
    class Role(models.TextChoices):
        LEARNER = "LEARNER", "Learner"
        INSTRUCTOR = "INSTRUCTOR", "Instructor"
        ADMIN = "ADMIN", "Admin"

    class LearnerType(models.TextChoices):
        BREEDER = "BREEDER", "Breeder"
        VET = "VET", "Veterinarian"
        VET_STUDENT = "VET_STUDENT", "Veterinary student"
        OTHER = "OTHER", "Other"

    user = models.OneToOneField(
        "accounts.User", on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField(max_length=32, blank=True)
    whatsapp_number = models.CharField(max_length=32, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default="NG")

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.LEARNER
    )
    learner_type = models.CharField(
        max_length=20, choices=LearnerType.choices, blank=True
    )
    kennel_name = models.CharField(max_length=255, blank=True)
    vcn_number = models.CharField(max_length=50, blank=True)
    years_experience = models.PositiveIntegerField(null=True, blank=True)
    marketing_opt_in = models.BooleanField(default=False)
    # Build spec §10: "Email verification required before enrollment
    # activates." Login isn't blocked by this (User.is_active handles
    # that separately) — only the checkout flow checks it, via
    # apps.payments.views.checkout.
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile: {self.user.email}"
