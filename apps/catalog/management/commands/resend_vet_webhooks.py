from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Course
from apps.catalog.webhooks import notify_course_published

# One-time: resends the course.published webhook to Xpress Vet
# Marketplace for the courses that never actually got it, despite
# apply_vet_blog_credit_and_publish and fix_pet_owner_education_webhook_line
# both reporting success.
#
# Root cause (confirmed against Vet Marketplace's own coursepublishdrafts
# collection on 2026-09-02): those two commands were run locally against
# the prod DB (this project's normal workflow for one-time commands), but
# this project's local .env has no VET_COURSE_PUBLISH_WEBHOOK_URL/SECRET
# — only Render's deployed env does. notify_course_published() read a
# blank URL and returned immediately, before sending anything or logging
# anything, so both commands' "Notified Vet Marketplace: ..." output was
# true about the call happening, not about anything actually being sent.
#
# The 19 courses that DID sync went through the live admin
# publish_selected_courses action running on Render itself, where the
# real secret is present.
#
# MISSING_SLUGS below = this batch's full 50-slug list minus the 19
# slugs Vet Marketplace confirmed already having (from their own DB dump
# of coursepublishdrafts, 2026-09-02). Their receiver is idempotent by
# slug (matches {slug, status: 'draft'} and updates in place), so this
# is safe to re-run even if it double-sends.
MISSING_SLUGS = [
    # Poultry
    "fowlpox-in-chickens-and-turkeys",
    "colibacillosis-in-poultry",
    "chicken-anemia-virus-infection",
    "helminthiasis-in-poultry",
    "histomoniasis-blackhead-disease",
    "external-parasites-in-poultry",
    "broiler-feeding-and-management",
    "poultry-heat-stress-management",
    "ascites-syndrome-in-broilers",
    "broiler-sudden-death-syndrome",
    "egg-production-problems",
    # Dogs
    "ehrlichiosis-tick-borne-disease-dogs",
    "heartworm-mosquito-borne-parasites-dogs",
    "gastric-dilatation-volvulus-bloat",
    "common-skin-disorders-in-dogs",
    # Cats
    "feline-upper-respiratory-infections",
    "feline-parasites-deworming-schedules",
    "felv-fiv-in-cats",
    "feline-flutd-urinary-blockage",
    "feline-chronic-kidney-disease",
    "feline-infectious-peritonitis-fip",
    "hyperthyroidism-in-cats",
    "feline-diabetes-mellitus",
    "cat-bite-abscesses",
    # Livestock
    "foot-and-mouth-disease-in-cattle",
    "contagious-bovine-pleuropneumonia",
    # Pet Owner Education (GENERAL) — none of these 5 ever synced
    "recognizing-a-veterinary-emergency",
    "zoonotic-diseases-every-pet-owner-should-know",
    "nutrition-basics-puppies-kittens-adults",
    "vaccination-schedules-puppies-kittens",
    "parasite-prevention-deworming-flea-tick",
]


class Command(BaseCommand):
    help = (
        "One-time: resends the course.published webhook to Xpress Vet Marketplace "
        "for the 31 courses that were published but never actually notified, due "
        "to a local run missing the webhook secret. Refuses to run at all unless "
        "VET_COURSE_PUBLISH_WEBHOOK_URL/SECRET are actually configured in this "
        "environment, so it can't repeat the exact silent failure it's fixing."
    )

    def handle(self, *args, **options):
        from django.conf import settings

        if not getattr(settings, "VET_COURSE_PUBLISH_WEBHOOK_URL", "") or not getattr(
            settings, "VET_COURSE_PUBLISH_WEBHOOK_SECRET", ""
        ):
            raise CommandError(
                "VET_COURSE_PUBLISH_WEBHOOK_URL / VET_COURSE_PUBLISH_WEBHOOK_SECRET "
                "are not set in this environment — running here would silently skip "
                "every course again, exactly like the runs that caused this. Run this "
                "command somewhere those two are actually configured (e.g. with them "
                "pasted in alongside DATABASE_URL, pulled from Render's Environment "
                "tab — never hardcoded). Aborting without sending anything."
            )

        if "localhost" in settings.SITE_URL or "127.0.0.1" in settings.SITE_URL:
            # Real incident: this project's local .env correctly has
            # SITE_URL=http://localhost:8000 for actual local dev, but
            # nothing in the paste block that sets DATABASE_URL/the webhook
            # vars for a "production" run also overrides SITE_URL -- so it
            # silently fell through to the local .env value, and every
            # course_url in this run's payloads pointed at localhost. One
            # of those already reached 28 real subscribers as a dead link
            # before this check existed. webhooks.py now also refuses to
            # send with a localhost SITE_URL, but check it here too so this
            # command fails loudly up front instead of quietly reporting
            # "failed" 31 times.
            raise CommandError(
                f"SITE_URL is {settings.SITE_URL!r} — looks like a local/dev value, not "
                "production. Set it explicitly for this run too, e.g.:\n"
                '  $env:SITE_URL = "https://xpress-academy-web.onrender.com"\n'
                "Aborting without sending anything."
            )

        # Print exactly what this run will use — not a secret, but the two
        # previous runs both reported success while silently hitting the
        # wrong host, so print proof instead of trusting the return value
        # alone. The secret itself is never printed, only its length, as a
        # fingerprint to confirm the right one was pasted without exposing it.
        self.stdout.write(f"Target URL this run will POST to: {settings.VET_COURSE_PUBLISH_WEBHOOK_URL}")
        self.stdout.write(f"course_url values in this run's payloads will use SITE_URL: {settings.SITE_URL}")
        self.stdout.write(f"Secret configured: {len(settings.VET_COURSE_PUBLISH_WEBHOOK_SECRET)} character(s).")

        courses = {c.slug: c for c in Course.objects.filter(slug__in=MISSING_SLUGS)}
        missing_locally = set(MISSING_SLUGS) - set(courses)
        if missing_locally:
            self.stdout.write(self.style.WARNING(
                f"{len(missing_locally)} expected course(s) not found in this DB — skipping: {sorted(missing_locally)}"
            ))

        sent, failed, skipped = 0, 0, 0
        for slug in MISSING_SLUGS:
            course = courses.get(slug)
            if not course:
                continue
            if not course.is_published:
                self.stdout.write(self.style.WARNING(f"  {slug}: not published — skipped."))
                skipped += 1
                continue
            result = notify_course_published(course)
            if result is True:
                self.stdout.write(self.style.SUCCESS(f"  Sent: {course.title}"))
                sent += 1
            elif result is False:
                self.stdout.write(self.style.ERROR(f"  FAILED (see logs above): {course.title}"))
                failed += 1
            else:
                self.stdout.write(self.style.WARNING(f"  Skipped (no destination configured): {course.title}"))
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done. Sent {sent}, failed {failed}, skipped {skipped} (of {len(MISSING_SLUGS)} expected)."
        ))
        if sent and not failed:
            self.stdout.write(self.style.SUCCESS(
                "All sent successfully — ask Vet Marketplace to confirm the count in coursepublishdrafts."
            ))
