from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

# The "Course Manager" role: everything a day-to-day Academy manager
# needs (courses, instructor review/verification, learner support,
# ops-queue triage) and nothing financial, no user-account edit rights
# (change permission on accounts.User would let a holder promote
# themselves to superuser), and no system/automation config.
#
# Deliberately no delete permission anywhere — matches the rest of
# this codebase's "trusted staff console, but no destructive-by-
# default actions" posture (see EarningsEntry/Payment admin, which
# hard-disable delete/change in code rather than relying on Group
# scoping alone).
#
# Idempotent: safe to re-run (get_or_create + a fixed permission set
# assigned via .set(), same pattern as the seed_* course commands).

GROUP_NAME = "Course Manager"

# (app_label, model_name, [codename actions]) -> codenames are
# Django's standard "add_", "change_", "view_" prefixes.
PERMISSIONS = [
    # Course content — full authoring rights, no delete.
    ("catalog", "programme", ["add", "change", "view"]),
    ("catalog", "course", ["add", "change", "view"]),
    ("catalog", "module", ["add", "change", "view"]),
    ("catalog", "lesson", ["add", "change", "view"]),
    ("catalog", "resource", ["add", "change", "view"]),
    ("catalog", "coursefaq", ["add", "change", "view"]),
    # Instructor review / verification / moderation.
    ("instructors", "vertical", ["add", "change", "view"]),
    ("instructors", "instructor", ["change", "view"]),  # verify via admin action, not create
    ("instructors", "instructordocument", ["add", "change", "view"]),
    ("instructors", "coursereview", ["change", "view"]),  # rounds are created by the service layer
    ("instructors", "courserating", ["change", "view"]),  # moderation (remove_for_abuse)
    # Learner support inbox.
    ("support", "supportticket", ["change", "view"]),
    ("support", "supportmessage", ["add", "change", "view"]),  # reply box is an inline on the ticket
    # Ops queue triage only — not SignalRule/InterruptBudget/DigestRun/
    # CalendarObligation, which are automation config, not day-to-day work.
    ("operations", "signal", ["change", "view"]),
]

EXCLUDED_NOTE = (
    "Explicitly NOT granted: accounts.User/Profile (change perm here is a "
    "privilege-escalation path to is_superuser), payments.* (Payment/Coupon/"
    "Partner/ReconciliationFlag), instructors.EarningsEntry/Payout, "
    "operations.SignalRule/InterruptBudget/DigestRun/CalendarObligation/"
    "InterruptLog, organizations.Organization, certificates.CertificateSequence."
)


class Command(BaseCommand):
    help = (
        "Creates (or updates) the 'Course Manager' Django Group with exactly "
        "the model permissions a day-to-day Academy manager needs. Assign a "
        "User to this Group and set is_staff=True (leave is_superuser=False) "
        "to grant the role. Safe to re-run."
    )

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name=GROUP_NAME)

        wanted_codenames = set()
        missing = []
        for app_label, model_name, actions in PERMISSIONS:
            try:
                ct = ContentType.objects.get(app_label=app_label, model=model_name)
            except ContentType.DoesNotExist:
                missing.append(f"{app_label}.{model_name}")
                continue
            for action in actions:
                codename = f"{action}_{model_name}"
                wanted_codenames.add(codename)
                perm, _ = Permission.objects.get_or_create(
                    content_type=ct, codename=codename,
                    defaults={"name": f"Can {action} {model_name}"},
                )

        perms = Permission.objects.filter(
            content_type__app_label__in={p[0] for p in PERMISSIONS},
            codename__in=wanted_codenames,
        )
        group.permissions.set(perms)

        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} '{GROUP_NAME}' group with {perms.count()} permission(s)."
        ))
        if missing:
            self.stdout.write(self.style.WARNING(
                "Skipped (content type not found, check app_label/model_name): "
                + ", ".join(missing)
            ))
        self.stdout.write(self.style.NOTICE(EXCLUDED_NOTE))
        self.stdout.write(
            "Reminder: /ops/growth/ (revenue dashboard) checks only is_staff, "
            "not this Group's permissions — anyone with is_staff=True can see "
            "it regardless of Group membership. No code-level fix exists for "
            "that yet."
        )
