from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import RateLimitedAuthenticationForm

app_name = "accounts"

urlpatterns = [
    path("login/", views.TwoFactorLoginView.as_view(
        template_name="registration/login.html", authentication_form=RateLimitedAuthenticationForm,
    ), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("2fa/verify/", views.twofactor_verify, name="twofactor_verify"),
    path("2fa/setup/", views.twofactor_setup, name="twofactor_setup"),
    path("2fa/disable/", views.twofactor_disable, name="twofactor_disable"),
    path("signup/", views.signup, name="signup"),
    path("verify/<str:token>/", views.verify_email, name="verify_email"),
    path("resend-verification/", views.resend_verification, name="resend_verification"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    # path, not str: the token embeds a slice of the user's raw
    # PBKDF2 password hash (see _make_reset_token), which uses
    # standard (non-urlsafe) base64 and can contain a literal "/" —
    # <str:...> excludes "/" and 404s whenever that happens to occur,
    # a real bug caught by a test that got unlucky/lucky depending on
    # how you look at it, since the hash bytes are random per-user.
    path("reset-password/<path:token>/", views.reset_password, name="reset_password"),
]
