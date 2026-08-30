from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Emergency 2FA reset — runs directly against the database, not
    through any web session. This is the recovery path when the
    ACCOUNT OWNER's own account is what's stuck (lost authenticator,
    backup codes burned) and they can't log into the admin at all to
    use UserAdmin.reset_two_factor (the click-based action, which
    needs someone else's already-authenticated session and so can't
    help the owner recover their own). Same local-workflow-against-
    prod-DATABASE_URL pattern as every other one-off command this
    project — see the project's own README/deploy notes."""

    help = (
        "Deletes all TOTP/backup-code devices for a user, so they can log back "
        "in with just their password. Works even when the account is currently "
        "locked out of the web login entirely."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        from django_otp.plugins.otp_static.models import StaticDevice
        from django_otp.plugins.otp_totp.models import TOTPDevice

        User = get_user_model()
        email = options["email"].strip()
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise CommandError(f"No user found for {email}")

        totp_deleted, _ = TOTPDevice.objects.filter(user=user).delete()
        static_deleted, _ = StaticDevice.objects.filter(user=user).delete()
        self.stdout.write(self.style.SUCCESS(
            f"Two-factor authentication reset for {email} — removed {totp_deleted} TOTP "
            f"device(s) and {static_deleted} backup-code device/token row(s). "
            f"They can log in with just their password now."
        ))
