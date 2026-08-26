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


class LoginAttempt(models.Model):
    """Every login attempt, success or failure, by attempted email —
    the only thing standing between this app and unlimited password
    guessing against any known account. Django's stock LoginView (used
    directly in urls.py) has zero built-in throttling on its own.

    DB-backed rather than cache-backed deliberately — this whole app
    runs without Redis on the free tier (see engagement/operations
    task scheduling elsewhere), so a cache-based rate limiter isn't a
    real option here; a plain indexed table, queried over a short
    recent window, is cheap enough at this scale. See
    apps.accounts.forms.RateLimitedAuthenticationForm for the actual
    lockout logic that reads this."""

    email = models.EmailField(db_index=True)
    successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} — {'ok' if self.successful else 'failed'} — {self.created_at:%Y-%m-%d %H:%M}"


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
