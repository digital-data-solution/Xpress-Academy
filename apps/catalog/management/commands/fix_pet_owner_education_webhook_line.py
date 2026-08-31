from django.core.management.base import BaseCommand

from apps.catalog.models import Course, Programme
from apps.catalog.webhooks import notify_course_published

# Real gap found while investigating why the 5 Pet Owner Education
# courses never showed up in Xpress Vet Marketplace's "Academy
# Courses" dashboard: the "Pet Owner Education" Programme was created
# (see seed_recognizing_vet_emergency_course.py and its 4 sibling
# commands) without setting webhook_line, defaulting to
# Programme.WebhookLine.NONE — unlike every other cross-promotion
# Programme in this batch (Veterinary Continuing Education, Dog
# Breeding Courses), which are correctly wired to VET.
#
# The seed commands themselves are now fixed to set webhook_line=VET
# going forward — this command is the one-time retroactive fix for
# the Programme row and the 5 courses that already published under
# the wrong (missing) routing, so Vet Marketplace actually gets
# notified about them now instead of silently never finding out.

PET_OWNER_EDUCATION_SLUGS = [
    "recognizing-a-veterinary-emergency",
    "zoonotic-diseases-every-pet-owner-should-know",
    "nutrition-basics-puppies-kittens-adults",
    "vaccination-schedules-puppies-kittens",
    "parasite-prevention-deworming-flea-tick",
]


class Command(BaseCommand):
    help = (
        "One-time: fixes the 'Pet Owner Education' Programme's webhook_line "
        "(was NONE, should be VET) and retroactively fires the course-publish "
        "webhook for its 5 already-published courses. Safe to re-run — the "
        "retroactive notification only fires once (guarded on the Programme "
        "fix actually happening), never re-sent on a later run, since Vet "
        "Marketplace's webhook receiver isn't known to dedupe by slug."
    )

    def handle(self, *args, **options):
        programme = Programme.objects.filter(slug="pet-owner-education").first()
        if not programme:
            self.stderr.write(self.style.ERROR("No 'Pet Owner Education' Programme found — nothing to fix."))
            return

        needs_fix = programme.webhook_line != Programme.WebhookLine.VET
        if needs_fix:
            programme.webhook_line = Programme.WebhookLine.VET
            programme.save(update_fields=["webhook_line"])
            self.stdout.write(self.style.SUCCESS(
                "Fixed 'Pet Owner Education' Programme: webhook_line NONE -> VET."
            ))
        else:
            self.stdout.write(
                "'Pet Owner Education' Programme already routes to VET — already fixed on a prior run, "
                "not re-notifying Vet Marketplace (its receiver isn't known to dedupe by slug)."
            )
            return

        notified, skipped = 0, 0
        for slug in PET_OWNER_EDUCATION_SLUGS:
            course = Course.objects.filter(slug=slug).first()
            if not course:
                self.stdout.write(self.style.WARNING(f"  {slug}: not found — skipped."))
                skipped += 1
                continue
            if not course.is_published:
                self.stdout.write(self.style.WARNING(f"  {slug}: not published yet — skipped."))
                skipped += 1
                continue
            notify_course_published(course)
            notified += 1
            self.stdout.write(f"  Notified Vet Marketplace: {course.title}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Retroactively notified {notified} course(s), skipped {skipped}."
        ))
