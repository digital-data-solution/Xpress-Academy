from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourteenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("The Main External Parasites",
     """<h2>Red/poultry mite — the most economically significant, and the trickiest</h2>
<p>The red or poultry mite (Dermanyssus gallinae) is the most economically significant external parasite in many systems, and it's genuinely different from the others on this list: it's NOCTURNAL, hiding in cracks and crevices by day and feeding on birds only at night. It causes anemia, restlessness, and reduced lay, and — critically — it survives off the bird for MONTHS, meaning the housing itself becomes part of the infestation, not just the birds.</p>
<h2>Northern fowl mite, scaly leg mite, lice, and ticks</h2>
<p>The northern fowl mite (Ornithonyssus sylviarum) lives on the bird continuously, causing feather damage and anemia particularly in layers. Scaly leg mite (Knemidocoptes mutans) burrows under leg scales, producing a distinctive presentation of crusty, deformed legs. Lice feed on feathers and skin debris — less directly damaging than the blood-feeding mites. Ticks are less universally significant in most systems but can transmit other infections.</p>"""),
    ("Clinical Signs and Diagnosis",
     """<h2>What you'll see</h2>
<p>Restlessness, feather damage or loss, reduced egg production, a pale comb from anemia with heavy blood-feeding infestations, and visible parasites or their eggs on direct inspection.</p>
<h2>Why daytime inspection can miss the most important parasite entirely</h2>
<p>Direct visual inspection of both birds AND housing — cracks, crevices, perch ends — is the standard diagnostic approach. But for red mite SPECIFICALLY, this needs to happen at NIGHT, or with a torch checking cracks during the day. A daytime, bird-only inspection routinely underestimates red mite burden, simply because the mites aren't on the birds when you're looking — they're hidden in the housing itself, exactly as covered in the previous module.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treat the housing, not just the bird</h2>
<p>An appropriate miticide or insecticide, chosen with veterinary guidance given resistance and withdrawal-period concerns, is the standard treatment. But because red mite lives mainly in the ENVIRONMENT rather than on the bird, treating the housing cracks matters just as much as treating the birds themselves — treating birds alone is a common, well-documented reason infestations recur despite apparently successful treatment.</p>
<h2>Prevention</h2>
<p>Thorough cleaning between batches removes the organic debris that shelters mites. Regular red-mite-specific housing inspection (not just bird inspection), general hygiene and litter management, quarantining new birds, and range rotation round out a real prevention program.</p>
<h2>Why heavy infestations cost more than they look like they should</h2>
<p>Production loss comes from both real blood loss and chronic stress together — the visible signs (feather damage, restlessness) understate the total production impact of a heavy infestation.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does red mite (Dermanyssus gallinae) present a genuinely different control challenge from other external parasites?",
        "It's nocturnal, hides in housing cracks and crevices by day, and survives off the bird for months — the "
        "housing itself becomes part of the infestation, not just the birds.",
        "It lives mainly in the housing environment rather than continuously on the bird, unlike most other parasites here",
        "Red mite behaves identically to the northern fowl mite in every relevant respect",
    ),
    (
        "Why does a daytime, bird-only inspection routinely underestimate red mite burden?",
        "Red mite is nocturnal and hides in housing cracks during the day, so it's simply not on the birds when a "
        "daytime inspection is looking for it — a night check or torch-lit crack inspection is needed instead.",
        "Red mite hides in housing cracks during the day and isn't present on birds when a daytime check occurs",
        "Daytime and nighttime inspections always find the same red mite burden regardless of timing",
    ),
    (
        "Why does treating birds alone often fail to resolve a red mite infestation?",
        "Because the mite lives mainly in the environment rather than on the bird, leaving the housing cracks "
        "untreated allows the infestation to persist and recur even after the birds themselves are treated.",
        "The mite lives mainly in the environment, so untreated housing cracks let the infestation recur",
        "Treating birds alone is always fully sufficient to eliminate any red mite infestation permanently",
    ),
    (
        "Why does scaly leg mite (Knemidocoptes mutans) produce a distinctive presentation compared to other external parasites here?",
        "It burrows under the leg scales specifically, producing crusty, deformed legs — a visibly different "
        "presentation from the feather/skin-focused damage caused by mites, lice, and ticks elsewhere on the bird.",
        "It burrows under leg scales specifically, producing a visibly distinct crusty, deformed-leg presentation",
        "Scaly leg mite produces the exact same clinical presentation as the northern fowl mite",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'External Parasites in Poultry: Mites, Lice, and Ticks' — fourteenth of "
        "the poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="veterinary-continuing-education",
            defaults={
                "title": "Veterinary Continuing Education",
                "audience": Audience.VET,
                "description": "Clinical continuing-education courses for licensed veterinarians and vet techs.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="external-parasites-in-poultry",
                defaults={
                    "title": "External Parasites in Poultry: Mites, Lice, and Ticks",
                    "subtitle": "One mite lives on the bird. Another lives in the house and only visits at night "
                                 "— exactly why a daytime inspection can miss it completely.",
                    "description": "<p>A 3-module continuing-education course on external poultry parasites — "
                                    "the main mite, lice, and tick types including red mite's nocturnal "
                                    "housing-based lifecycle, clinical signs and why inspection timing matters, "
                                    "and treatment/control/prevention centered on treating housing, not just "
                                    "birds.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "A daytime bird check can completely miss your worst parasite problem",
                    "sales_subheadline": "3 modules on external parasites — red mite's nocturnal housing lifecycle, "
                                          "diagnosis, and why treating housing matters as much as treating birds.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners investigating a recurring infestation despite prior treatment\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "External parasites CE for vets — red mite's housing lifecycle, "
                                         "diagnosis, and treating housing not just birds.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                return

            self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
            for i, (title, body) in enumerate(MODULES, start=1):
                module = Module.objects.create(
                    course=course, order=i, title=title, unlock_rule=Module.UnlockRule.SEQUENTIAL,
                )
                Lesson.objects.create(
                    module=module, order=1, title=f"Module {i}: {title}", type=Lesson.Type.TEXT,
                    body=body.strip(), is_preview=(i == 1),
                )
            self.stdout.write(self.style.SUCCESS(f"  {len(MODULES)} modules created with real written content."))

            bank = QuestionBank.objects.create(
                organization=org, name="External Parasites in Poultry — Final Exam",
                description="Covers all 3 modules — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course,
                title="Final Exam — External Parasites in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
