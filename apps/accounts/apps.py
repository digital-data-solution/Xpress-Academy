from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    def ready(self):
        from . import signal_receivers
        signal_receivers.connect()
        _redirect_admin_login_through_2fa()


def _redirect_admin_login_through_2fa():
    """Django's admin has its OWN built-in login view/form
    (AdminSite.login), completely separate from apps.accounts.urls'
    TwoFactorLoginView — a staff member whose session has expired and
    who goes straight to the admin URL would authenticate through
    Django's stock form, bypassing 2FA entirely, even though it's
    fully wired on the public-facing /account/login/. Real gap: the
    whole point of "every staff account's login" was staff logins
    specifically, and staff logging in via the admin URL is the common
    case, not the exception. Fixed the simplest way that's still
    correct: point admin.site.login at our own login view instead of
    rendering Django's — the same TwoFactorLoginView (and RateLimitedAuthenticationForm)
    handles it either way, so there's exactly one login/2FA code path,
    not two to keep in sync."""
    from django.contrib import admin
    from django.shortcuts import redirect
    from django.urls import reverse

    def login_redirect(request, extra_context=None):
        next_url = request.GET.get("next") or reverse("admin:index")
        return redirect(f"{reverse('accounts:login')}?next={next_url}")

    admin.site.login = login_redirect
