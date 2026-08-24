from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import SetPasswordForm
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import ForgotPasswordForm, SignupForm
from .models import User

VERIFY_SALT = "accounts.email-verify"
VERIFY_MAX_AGE_SECONDS = 60 * 60 * 48  # 48h

RESET_SALT = "accounts.password-reset"
RESET_MAX_AGE_SECONDS = 60 * 60  # 1h — shorter-lived than email verification, this is more sensitive


def _make_verify_token(user: User) -> str:
    return TimestampSigner(salt=VERIFY_SALT).sign(str(user.pk))


def _send_verification_email(user: User):
    from django.conf import settings
    from django.template.loader import render_to_string

    from apps.engagement.services import send_email

    token = _make_verify_token(user)
    send_email(
        to_email=user.email, user=user, template_key="verify_email", subject="Verify your email — Xpress Digital Academy",
        html=render_to_string("emails/verify_email.html", {
            "first_name": user.first_name or "there",
            "verify_url": f"{settings.SITE_URL}/account/verify/{token}/",
            "site_url": settings.SITE_URL,
        }),
        dedupe_key=f"verify_email:{user.id}:{token[-12:]}",  # a fresh token each send, so a resend isn't blocked
    )


def signup(request):
    if request.user.is_authenticated:
        return redirect("enrollment:dashboard")

    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            _send_verification_email(user)
            login(request, user)
            messages.success(request, "Welcome! Check your email to verify your account before enrolling in a course.")
            return redirect("enrollment:dashboard")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


def verify_email(request, token):
    signer = TimestampSigner(salt=VERIFY_SALT)
    try:
        user_id = signer.unsign(token, max_age=VERIFY_MAX_AGE_SECONDS)
    except SignatureExpired:
        messages.error(request, "That verification link has expired. Log in and we'll send a new one.")
        return redirect("accounts:login")
    except BadSignature:
        messages.error(request, "That verification link isn't valid.")
        return redirect("accounts:login")

    user = User.objects.filter(pk=user_id).first()
    if not user:
        messages.error(request, "That verification link isn't valid.")
        return redirect("accounts:login")

    user.profile.email_verified = True
    user.profile.save(update_fields=["email_verified"])
    messages.success(request, "Email verified — you're all set.")
    return redirect("enrollment:dashboard" if request.user.is_authenticated else "accounts:login")


@require_POST
def resend_verification(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    if request.user.profile.email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        _send_verification_email(request.user)
        messages.success(request, "Verification email sent.")
    return redirect("enrollment:dashboard")


def _make_reset_token(user: User) -> str:
    # Embeds a fragment of the current password hash in the signed
    # payload, not just the user's pk. Once the password actually
    # changes, that fragment no longer matches — so a reset link is
    # single-use without needing separate token-storage/invalidation
    # state. Same trick Django's own PasswordResetTokenGenerator uses.
    return TimestampSigner(salt=RESET_SALT).sign(f"{user.pk}:{user.password[-12:]}")


def _send_password_reset_email(user: User):
    from django.conf import settings
    from django.template.loader import render_to_string

    from apps.engagement.services import send_email

    token = _make_reset_token(user)
    send_email(
        to_email=user.email, user=user, template_key="password_reset",
        subject="Reset your password — Xpress Digital Academy",
        html=render_to_string("emails/password_reset.html", {
            "first_name": user.first_name or "there",
            "reset_url": f"{settings.SITE_URL}/account/reset-password/{token}/",
            "site_url": settings.SITE_URL,
        }),
        dedupe_key=f"password_reset:{user.id}:{token[-12:]}",
    )


def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.filter(email__iexact=email).first()
            if user:
                _send_password_reset_email(user)
            # Same message regardless of whether the account exists —
            # doesn't confirm/deny an email is registered to a stranger
            # probing the form (standard practice, not paranoia here:
            # this is a public, unauthenticated form).
            messages.success(request, "If that email has an account, we've sent a password reset link.")
            return redirect("accounts:login")
    else:
        form = ForgotPasswordForm()

    return render(request, "registration/forgot_password.html", {"form": form})


def reset_password(request, token):
    signer = TimestampSigner(salt=RESET_SALT)
    try:
        payload = signer.unsign(token, max_age=RESET_MAX_AGE_SECONDS)
    except SignatureExpired:
        messages.error(request, "That reset link has expired. Request a new one below.")
        return redirect("accounts:forgot_password")
    except BadSignature:
        messages.error(request, "That reset link isn't valid.")
        return redirect("accounts:forgot_password")

    user_id, _, hash_fragment = payload.partition(":")
    user = User.objects.filter(pk=user_id).first()
    if not user or user.password[-12:] != hash_fragment:
        # Missing user, or the password already changed since this
        # link was issued (a prior use of the same link, most likely).
        messages.error(request, "That reset link has already been used or is no longer valid.")
        return redirect("accounts:forgot_password")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password reset — log in with your new password.")
            return redirect("accounts:login")
    else:
        form = SetPasswordForm(user)

    return render(request, "registration/reset_password.html", {"form": form})
