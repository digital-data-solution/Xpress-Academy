from django.contrib import messages
from django.contrib.auth import login, views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django_otp import login as otp_login
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

from .forms import ForgotPasswordForm, SignupForm, TOTPTokenForm
from .models import User

VERIFY_SALT = "accounts.email-verify"
VERIFY_MAX_AGE_SECONDS = 60 * 60 * 48  # 48h

RESET_SALT = "accounts.password-reset"
RESET_MAX_AGE_SECONDS = 60 * 60  # 1h — shorter-lived than email verification, this is more sensitive

# Both _send_verification_email and _send_password_reset_email use a
# dedupe_key that's deliberately unique per call (includes a slice of
# the freshly-signed token, which changes every time) — so a genuine
# resend is never blocked by send_email()'s own dedupe. That's correct
# behaviour, but it also means nothing stopped rapid repeated clicks
# (or, for forgot_password specifically, repeated unauthenticated form
# submissions from anyone who knows a real email) from sending real
# email after real email with zero limit. This cooldown is that limit.
RESEND_COOLDOWN_SECONDS = 120


def _recently_sent(user, template_key: str) -> bool:
    from apps.engagement.models import EmailLog

    cutoff = timezone.now() - timezone.timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    return EmailLog.objects.filter(user=user, template_key=template_key, created_at__gte=cutoff).exists()


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
    elif _recently_sent(request.user, "verify_email"):
        messages.info(request, "We just sent that — check your inbox (and spam folder) before requesting another.")
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
            if user and not _recently_sent(user, "password_reset"):
                _send_password_reset_email(user)
            # Same message regardless of whether the account exists, or
            # even whether an email was actually sent this time (rate
            # limited) — doesn't confirm/deny an email is registered to
            # a stranger probing the form (standard practice, not
            # paranoia here: this is a public, unauthenticated form).
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


# --- Two-factor authentication (real TOTP, RFC 6238) -----------------
#
# Confirmed cross-portfolio decision, 2026-08-30 — the owner and every
# staff account, not an interim control. Opt-in per account, never a
# surprise lockout: 2FA is only required at login for a user who has
# actually confirmed a device via twofactor_setup below. django-otp's
# TOTPDevice/StaticDevice primitives are used directly (proven,
# standard TOTP + backup-code implementations) rather than adopting
# django-two-factor-auth's own login view/URL wizard, which assumes a
# fairly vanilla auth setup — this codebase's login already runs
# through a customized LoginView (RateLimitedAuthenticationForm), and
# a lower-level integration fits that existing shape far better than
# replacing it outright.

PENDING_2FA_SESSION_KEY = "pending_2fa_user_id"
PENDING_2FA_REDIRECT_KEY = "pending_2fa_redirect"
PENDING_2FA_ATTEMPTS_KEY = "pending_2fa_attempts"
TWOFACTOR_VERIFY_MAX_ATTEMPTS = 5
BACKUP_CODE_COUNT = 10


class TwoFactorLoginView(auth_views.LoginView):
    """Same stock LoginView + RateLimitedAuthenticationForm as before —
    only form_valid changes. A user with a confirmed TOTPDevice never
    gets logged in here directly; the password check succeeding just
    earns them a trip to twofactor_verify, which is what actually
    calls login()."""

    def form_valid(self, form):
        user = form.get_user()
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device is not None:
            self.request.session[PENDING_2FA_SESSION_KEY] = user.pk
            self.request.session[PENDING_2FA_REDIRECT_KEY] = self.get_success_url()
            return redirect("accounts:twofactor_verify")

        response = super().form_valid(form)
        if user.is_staff:
            messages.info(
                self.request,
                "Two-factor authentication isn't set up on your account yet — "
                "set it up now for stronger protection.",
            )
        return response


def _match_otp_device(user, token):
    """A live 6-digit TOTP code, or a single-use 8-character backup
    code — either one logs the second factor in. StaticDevice.verify_token
    deletes the matched StaticToken itself (django-otp's own behavior),
    so a backup code can never be reused. django-otp's ThrottlingMixin
    on TOTPDevice already rate-limits repeated wrong guesses against
    the device itself, on top of the session-attempt cap below."""
    totp = TOTPDevice.objects.filter(user=user, confirmed=True).first()
    if totp and totp.verify_token(token):
        return totp
    static = StaticDevice.objects.filter(user=user, confirmed=True).first()
    if static and static.verify_token(token):
        return static
    return None


def twofactor_verify(request):
    user_id = request.session.get(PENDING_2FA_SESSION_KEY)
    if not user_id:
        return redirect("accounts:login")
    user = User.objects.filter(pk=user_id).first()
    if not user:
        request.session.pop(PENDING_2FA_SESSION_KEY, None)
        return redirect("accounts:login")

    if request.method == "POST":
        form = TOTPTokenForm(request.POST)
        if form.is_valid():
            device = _match_otp_device(user, form.cleaned_data["token"])
            if device is not None:
                redirect_to = request.session.pop(PENDING_2FA_REDIRECT_KEY, None)
                request.session.pop(PENDING_2FA_SESSION_KEY, None)
                request.session.pop(PENDING_2FA_ATTEMPTS_KEY, None)
                login(request, user)
                otp_login(request, device)
                return redirect(redirect_to or "enrollment:dashboard")

            attempts = request.session.get(PENDING_2FA_ATTEMPTS_KEY, 0) + 1
            request.session[PENDING_2FA_ATTEMPTS_KEY] = attempts
            if attempts >= TWOFACTOR_VERIFY_MAX_ATTEMPTS:
                request.session.pop(PENDING_2FA_SESSION_KEY, None)
                request.session.pop(PENDING_2FA_REDIRECT_KEY, None)
                request.session.pop(PENDING_2FA_ATTEMPTS_KEY, None)
                messages.error(request, "Too many failed codes. Please log in again.")
                return redirect("accounts:login")
            form.add_error("token", "That code isn't valid. Try again.")
    else:
        form = TOTPTokenForm()

    return render(request, "registration/twofactor_verify.html", {"form": form})


@login_required
def twofactor_setup(request):
    existing = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
    if existing:
        return render(request, "registration/twofactor_setup.html", {"already_enabled": True})

    # get_or_create so refreshing this page mid-setup doesn't mint a
    # new secret/QR each time — the same unconfirmed device is reused
    # until it's actually confirmed below.
    device, _ = TOTPDevice.objects.get_or_create(
        user=request.user, confirmed=False, defaults={"name": "default"}
    )

    if request.method == "POST":
        form = TOTPTokenForm(request.POST)
        if form.is_valid() and device.verify_token(form.cleaned_data["token"]):
            device.confirmed = True
            device.save(update_fields=["confirmed"])

            # Backup codes: wipe any stale set from an earlier
            # abandoned setup, then mint a fresh batch. Shown once,
            # here — django-otp stores StaticToken.token in plaintext
            # by design (they're meant to be written down/saved by the
            # user, same as every other TOTP provider's recovery codes).
            StaticDevice.objects.filter(user=request.user).delete()
            static_device = StaticDevice.objects.create(user=request.user, name="backup codes", confirmed=True)
            codes = [StaticToken.random_token() for _ in range(BACKUP_CODE_COUNT)]
            StaticToken.objects.bulk_create(
                StaticToken(device=static_device, token=code) for code in codes
            )

            messages.success(request, "Two-factor authentication is now enabled.")
            return render(request, "registration/twofactor_backup_codes.html", {"codes": codes})
        form.add_error("token", "That code isn't valid. Check the app and try again.")
    else:
        form = TOTPTokenForm()

    return render(request, "registration/twofactor_setup.html", {
        "form": form, "device": device, "qr_data_uri": _totp_qr_data_uri(device),
        "secret": device.key,
    })


def _totp_qr_data_uri(device) -> str:
    import base64
    import io

    import qrcode

    img = qrcode.make(device.config_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


@require_POST
@login_required
def twofactor_disable(request):
    password = request.POST.get("password", "")
    if not request.user.check_password(password):
        messages.error(request, "Incorrect password — two-factor authentication was NOT disabled.")
        return redirect("accounts:twofactor_setup")

    TOTPDevice.objects.filter(user=request.user).delete()
    StaticDevice.objects.filter(user=request.user).delete()
    messages.success(request, "Two-factor authentication has been disabled on your account.")
    return redirect("accounts:twofactor_setup")
