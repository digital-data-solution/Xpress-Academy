from django.contrib import messages
from django.contrib.auth import login
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .forms import SignupForm
from .models import User

VERIFY_SALT = "accounts.email-verify"
VERIFY_MAX_AGE_SECONDS = 60 * 60 * 48  # 48h


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
