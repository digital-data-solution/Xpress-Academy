from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import User


class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    marketing_opt_in = forms.BooleanField(required=False, initial=False)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)  # uses AUTH_PASSWORD_VALIDATORS, not a hand-rolled rule
        return password

    def save(self):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data.get("last_name", ""),
        )
        # The post_save signal (signal_receivers.py) already created a
        # Profile row for this user — update it rather than creating a
        # second one, which would violate the OneToOne constraint.
        user.profile.marketing_opt_in = self.cleaned_data.get("marketing_opt_in", False)
        user.profile.save(update_fields=["marketing_opt_in"])
        return user


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15


class RateLimitedAuthenticationForm(AuthenticationForm):
    """Wired into apps.accounts.urls' LoginView via form_class= — see
    LoginAttempt's own docstring for why this exists at all. Locks out
    further attempts against a given email once LOGIN_LOCKOUT_THRESHOLD
    failures land within LOGIN_LOCKOUT_WINDOW_MINUTES, regardless of
    whether the next attempt's password would actually have been
    correct — the whole point is stopping a guessing script before it
    gets there, not just after."""

    def clean(self):
        from .models import LoginAttempt

        email = (self.cleaned_data.get("username") or "").strip().lower()  # AuthenticationForm's field is always named "username"

        if email:
            cutoff = timezone.now() - timezone.timedelta(minutes=LOGIN_LOCKOUT_WINDOW_MINUTES)
            recent_failures = LoginAttempt.objects.filter(
                email__iexact=email, successful=False, created_at__gte=cutoff,
            ).count()
            if recent_failures >= LOGIN_LOCKOUT_THRESHOLD:
                raise ValidationError(
                    "Too many failed login attempts on this account. "
                    "Please wait a few minutes and try again, or reset your password.",
                    code="too_many_attempts",
                )

        try:
            result = super().clean()
        except ValidationError:
            if email:
                LoginAttempt.objects.create(email=email, successful=False)
            raise

        if email:
            LoginAttempt.objects.create(email=email, successful=True)
        return result
