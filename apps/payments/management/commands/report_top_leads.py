from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.engagement.models import Lead
from apps.licensing.models import DiagnosticAttempt
from apps.payments.models import Payment


class Command(BaseCommand):
    help = (
        "Read-only report: ranks the best real leads to call right now, for handing to a "
        "telecaller. Three signal tiers -- abandoned/pending checkout (strongest: real "
        "purchase intent), diagnostic takers (especially low scorers -- a felt knowledge gap), "
        "and generic site leads (weakest signal, footer/catalog email capture). Contains real "
        "personal data (names, emails, phone numbers where on file) -- handle the output "
        "accordingly, don't paste it somewhere it can be indexed or leaked."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10, help="How many total leads to print.")
        parser.add_argument("--days", type=int, default=30, help="Only consider activity in the last N days.")

    def handle(self, *args, **options):
        limit = options["limit"]
        since = timezone.now() - timezone.timedelta(days=options["days"])

        rows = []

        # --- Tier 1: abandoned / pending checkout — real purchase intent ---
        payments = (
            Payment.objects.filter(
                status__in=[Payment.Status.PENDING, Payment.Status.ABANDONED],
                purpose=Payment.Purpose.COURSE_ACCESS,
                created_at__gte=since,
            )
            .select_related("user__profile", "course")
            .order_by("user_id", "-created_at")
        )
        seen_users = set()
        for p in payments:
            if p.user_id in seen_users:
                continue  # keep only the most recent attempt per user
            seen_users.add(p.user_id)
            profile = getattr(p.user, "profile", None)
            phone = (profile.whatsapp_number or profile.phone) if profile else ""
            name = f"{p.user.first_name} {p.user.last_name}".strip() or p.user.email
            course_title = p.course.title if p.course else "(no course)"
            reason = (
                f"Started checkout for \"{course_title}\" (₦{p.amount_kobo // 100:,}) "
                f"{p.created_at:%Y-%m-%d} and never completed -- status {p.status}."
            )
            rows.append({
                "tier": 1, "sort_key": (0, -p.created_at.timestamp()),
                "name": name, "email": p.user.email, "phone": phone,
                "stage": f"ABANDONED CHECKOUT ({p.status})", "reason": reason,
            })

        # --- Tier 2: diagnostic takers — felt knowledge gap, especially low scorers ---
        attempts = (
            DiagnosticAttempt.objects.filter(submitted_at__gte=since, submitted_at__isnull=False)
            .exclude(student_email="")
            .select_related("test")
            .order_by("-submitted_at")
        )
        phone_by_email = {
            u.email.lower(): (getattr(u, "profile", None) and (u.profile.whatsapp_number or u.profile.phone)) or ""
            for u in User.objects.filter(
                email__in=[a.student_email for a in attempts]
            ).select_related("profile")
        }
        for a in attempts:
            score = a.score_percent if a.score_percent is not None else 100
            phone = phone_by_email.get(a.student_email.lower(), "")
            reason = (
                f"Took the \"{a.test.title}\" free diagnostic on {a.submitted_at:%Y-%m-%d}, "
                f"scored {a.score_percent if a.score_percent is not None else '?'}% -- "
                f"{'a real gap the paid course would close.' if score < 60 else 'engaged enough to finish it.'}"
            )
            rows.append({
                "tier": 2, "sort_key": (1, score, -a.submitted_at.timestamp()),
                "name": a.student_name or a.student_email, "email": a.student_email, "phone": phone,
                "stage": f"DIAGNOSTIC TAKEN ({a.score_percent}%)" if a.score_percent is not None else "DIAGNOSTIC TAKEN",
                "reason": reason,
            })

        # --- Tier 3: generic site leads — weakest signal ---
        leads = Lead.objects.filter(created_at__gte=since).order_by("-created_at")
        phone_by_email2 = {
            u.email.lower(): (getattr(u, "profile", None) and (u.profile.whatsapp_number or u.profile.phone)) or ""
            for u in User.objects.filter(email__in=[l.email for l in leads]).select_related("profile")
        }
        for l in leads:
            phone = phone_by_email2.get(l.email.lower(), "")
            reason = f"Left an email via the '{l.source or 'unknown'}' capture point on {l.created_at:%Y-%m-%d}."
            rows.append({
                "tier": 3, "sort_key": (2, -l.created_at.timestamp()),
                "name": l.email, "email": l.email, "phone": phone,
                "stage": "SITE LEAD", "reason": reason,
            })

        rows.sort(key=lambda r: r["sort_key"])
        top = rows[:limit]

        if not top:
            self.stdout.write(self.style.WARNING(f"No lead activity found in the last {options['days']} day(s)."))
            return

        self.stdout.write(f"Top {len(top)} lead(s) to call, ranked by conversion likelihood:\n")
        for i, r in enumerate(top, 1):
            phone_display = r["phone"] or "NO PHONE ON FILE -- email only"
            self.stdout.write(f"{i}. {r['name']}")
            self.stdout.write(f"   Phone: {phone_display}")
            self.stdout.write(f"   Email: {r['email']}")
            self.stdout.write(f"   Stage: {r['stage']}")
            self.stdout.write(f"   Why:   {r['reason']}\n")

        no_phone = sum(1 for r in top if not r["phone"])
        if no_phone:
            self.stdout.write(self.style.WARNING(
                f"{no_phone} of {len(top)} have no phone number on file -- email/WhatsApp-via-email is the "
                f"only contact path for those unless someone looks them up another way."
            ))
