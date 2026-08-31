from django.core.management.base import BaseCommand

from apps.catalog.models import Course

# One-time command for the 50-course vet-blog cross-promotion batch
# built across this project's multi-round session (commits f4da7fc,
# 2bd76f9, 82527fe, 52cfcb3, 22de67d). Sam's explicit instruction:
# "for pet owners you can use my name as instructor, but for
# veterinarians use this as instructor Xpressvetmarketplace.com" —
# maps directly onto this batch's own Audience split. BREEDER
# audience (the one Responsible Dog Breeder's Curriculum course)
# wasn't addressed either way, so its instructor_bio is left as-is.
#
# Also publishes all 50 in the same pass (review_status=APPROVED,
# is_published=True via .save() per instance, same mechanism as the
# new CourseAdmin.publish_selected_courses action — see that action's
# own docstring for why no Vertical/domain_reviewer is required).

VET_MARKETPLACE_CREDIT = "Xpress Vet Marketplace (xpressvetmarketplace.com)"

# 44 VET-audience courses from this batch — instructor credit changes
# to Xpress Vet Marketplace.
VET_SLUGS = [
    "newcastle-disease-in-poultry",
    "fowl-typhoid-and-pullorum-disease",
    "canine-parvovirus",
    "peste-des-petits-ruminants",
    "mycoplasmosis-crd-in-poultry",
    "infectious-bronchitis-in-chickens",
    "brooding-day-old-chicks",
    "poultry-biosecurity-checklist",
    "fowlpox-in-chickens-and-turkeys",
    "mareks-disease-in-poultry",
    "colibacillosis-in-poultry",
    "poultry-nutrition-practical-guide",
    "avian-leukosis-in-poultry",
    "chicken-anemia-virus-infection",
    "avian-encephalomyelitis",
    "helminthiasis-in-poultry",
    "histomoniasis-blackhead-disease",
    "external-parasites-in-poultry",
    "broiler-feeding-and-management",
    "management-of-laying-hens",
    "poultry-heat-stress-management",
    "ascites-syndrome-in-broilers",
    "broiler-sudden-death-syndrome",
    "egg-production-problems",
    "canine-distemper",
    "ehrlichiosis-tick-borne-disease-dogs",
    "heartworm-mosquito-borne-parasites-dogs",
    "canine-rabies-prevention-exposure-protocol",
    "gastric-dilatation-volvulus-bloat",
    "common-skin-disorders-in-dogs",
    "feline-panleukopenia",
    "feline-upper-respiratory-infections",
    "feline-parasites-deworming-schedules",
    "foot-and-mouth-disease-in-cattle",
    "trypanosomiasis-in-livestock",
    "contagious-bovine-pleuropneumonia",
    "felv-fiv-in-cats",
    "feline-flutd-urinary-blockage",
    "feline-chronic-kidney-disease",
    "feline-infectious-peritonitis-fip",
    "hyperthyroidism-in-cats",
    "feline-diabetes-mellitus",
    "cat-bite-abscesses",
    "spaying-neutering-cats-timing-benefits",
]

# 5 GENERAL-audience "Pet Owner Education" courses — instructor credit
# stays Dr. Omale's own name (already the default set at creation).
GENERAL_SLUGS = [
    "recognizing-a-veterinary-emergency",
    "zoonotic-diseases-every-pet-owner-should-know",
    "nutrition-basics-puppies-kittens-adults",
    "vaccination-schedules-puppies-kittens",
    "parasite-prevention-deworming-flea-tick",
]

# 1 BREEDER-audience course — not addressed by Sam's instruction,
# instructor_bio left untouched. Still gets published in this pass.
BREEDER_SLUGS = [
    "responsible-dog-breeders-curriculum",
]

ALL_SLUGS = VET_SLUGS + GENERAL_SLUGS + BREEDER_SLUGS


class Command(BaseCommand):
    help = (
        "One-time: sets Xpress Vet Marketplace as instructor credit on the 44 "
        "VET-audience courses in the 50-course vet-blog batch, then publishes "
        "all 50 (VET + GENERAL Pet Owner Education + the 1 BREEDER course). "
        "Safe to re-run — idempotent."
    )

    def handle(self, *args, **options):
        courses = {c.slug: c for c in Course.objects.filter(slug__in=ALL_SLUGS)}

        missing = set(ALL_SLUGS) - set(courses)
        if missing:
            self.stdout.write(self.style.WARNING(
                f"{len(missing)} expected course(s) not found — skipping: {sorted(missing)}"
            ))

        credited = 0
        for slug in VET_SLUGS:
            course = courses.get(slug)
            if not course:
                continue
            if course.instructor_bio != VET_MARKETPLACE_CREDIT:
                course.instructor_bio = VET_MARKETPLACE_CREDIT
                credited += 1

        published, already = 0, 0
        for slug in ALL_SLUGS:
            course = courses.get(slug)
            if not course:
                continue
            was_published = course.is_published
            course.review_status = Course.ReviewStatus.APPROVED
            course.is_published = True
            course.save()  # per-instance save fires the publish webhook, same as admin
            if was_published:
                already += 1
            else:
                published += 1

        self.stdout.write(self.style.SUCCESS(
            f"Set Xpress Vet Marketplace instructor credit on {credited} VET course(s). "
            f"Published {published} course(s) ({already} were already published)."
        ))
