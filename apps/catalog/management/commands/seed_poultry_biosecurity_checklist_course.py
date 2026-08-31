from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Deepens
# the existing "Biosecurity Program Design" module in the earlier
# Poultry Health & Biosecurity course (seed_poultry_courses.py) into a
# standalone practical-checklist course — same relationship already
# established elsewhere in this batch.

MODULES = [
    ("Access Control and New Bird Introduction",
     """<h2>Two different jobs, not substitutes for each other</h2>
<p>Every poultry disease covered on this platform reaches a new farm the same handful of ways: a visitor's boots, untested new birds, contaminated equipment, or wild birds and rodents moving freely. Vaccination protects against a specific pathogen; biosecurity is what keeps every pathogen from arriving in the first place — the two aren't substitutes for one another.</p>
<h2>Access control that actually works</h2>
<p>Restrict visitor access to what's genuinely necessary. Footbaths and dedicated farm clothing/boots at house entrances only work if they're actually maintained — unchanged disinfectant in a footbath is close to useless, not a real barrier. Vehicle control means a designated drop-off point rather than vehicles driving up to the housing itself.</p>
<h2>The single highest-leverage decision on this list</h2>
<p>Quarantine new stock for two to three or more weeks in genuinely separate housing, with separate equipment and a separate staff order (visiting quarantined birds last, not first). A huge share of disease introductions covered elsewhere on this platform — fowl typhoid/pullorum, mycoplasmosis, Newcastle disease — trace back to skipping this step. Sourcing from certified or known-clean breeder flocks wherever possible is the single highest-leverage decision on this entire list. Never mix ages or sources without a real risk assessment first.</p>"""),
    ("All-In/All-Out and Cleaning",
     """<h2>Why continuous flocks make disease cycles nearly impossible to break</h2>
<p>Raising one batch as one group, then fully clearing and disinfecting between batches, breaks disease cycles that continuous topping-up simply can't. Continuous mixed-age flocks always have a susceptible younger bird available to keep an endemic pathogen circulating — the same pattern behind why mycoplasmosis and coccidiosis persist on some farms indefinitely.</p>
<h2>Cleaning is two separate steps, not one</h2>
<p>Organic matter must be removed BEFORE disinfecting — disinfectants are far less effective on dirty surfaces, and treating cleaning and disinfecting as one combined step is a common, costly shortcut. Genuine downtime of two or more weeks between batches breaks a disease cycle far better than a quick clean followed by immediate restocking.</p>
<h2>Matching disinfectant to target</h2>
<p>Disinfectant choice should match what you're actually trying to kill — coccidia oocysts specifically need a disinfectant labeled effective against them, since not every general-purpose disinfectant reaches them.</p>"""),
    ("Pest Control and the Real Test",
     """<h2>Rodents and wild birds as real, documented vectors</h2>
<p>Rodents are a documented vector for fowl typhoid and pullorum disease. Wild birds, waterfowl especially, are a recognized reservoir for Newcastle disease and avian influenza. Rodent-proof feed storage, controlling standing water, and screening housing where feasible are practical, concrete steps against both.</p>
<h2>The real test of any biosecurity measure</h2>
<p>Does a measure actually reduce a real transmission route, or does it just look thorough on paper? An unrefilled footbath, an unenforced quarantine, or a "no visitors" sign next to an open gate are common — and worthless. This is the honest standard every measure on this checklist should be held to, not just whether it exists on a farm's written protocol.</p>
<h2>Consistency over theoretical strength</h2>
<p>A moderately strong measure applied consistently beats a theoretically stronger measure applied inconsistently. Biosecurity failures on real farms are rarely about choosing the wrong measure — they're almost always about a real measure not being maintained.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why are vaccination and biosecurity described as not substitutes for one another?",
        "Vaccination protects against a specific pathogen a bird has been vaccinated for, while biosecurity is "
        "what keeps every pathogen — vaccinated against or not — from arriving on the farm in the first place.",
        "Vaccination protects against specific pathogens, while biosecurity keeps all pathogens from arriving at all",
        "Vaccination and biosecurity accomplish exactly the same protective function on a farm",
    ),
    (
        "Why is skipping quarantine on new stock repeatedly identified as a major cause of disease introduction?",
        "A huge share of real disease introductions (fowl typhoid/pullorum, mycoplasmosis, Newcastle disease) trace "
        "back specifically to new birds entering the flock without a genuine quarantine period first.",
        "New birds without genuine quarantine are a documented, recurring source of real disease introductions",
        "Quarantine has little real effect on introduction risk regardless of how it's implemented",
    ),
    (
        "Why must organic matter be removed before disinfecting, rather than combined into one cleaning step?",
        "Disinfectants are far less effective on dirty surfaces, so skipping the separate removal step meaningfully "
        "undermines how well the disinfection actually works.",
        "Disinfectants work far less effectively when organic matter hasn't been removed from the surface first",
        "Combining cleaning and disinfecting into one step produces the same result as doing them separately",
    ),
    (
        "According to the 'real test' for a biosecurity measure, what actually matters?",
        "Whether the measure genuinely reduces a real transmission route in practice — not whether it exists on "
        "paper or looks thorough, since an unmaintained measure (like an unrefilled footbath) is worthless.",
        "Whether the measure meaningfully reduces a real transmission route, not just how thorough it looks on paper",
        "Whether a measure exists in the farm's written protocol, regardless of how it's actually maintained",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Biosecurity on a Poultry Farm: A Practical Checklist' — fourth of the "
        "poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="poultry-biosecurity-checklist",
                defaults={
                    "title": "Biosecurity on a Poultry Farm: A Practical Checklist",
                    "subtitle": "Every disease on this platform reaches a farm the same handful of ways — this is "
                                 "the checklist that actually closes them.",
                    "description": "<p>A 3-module continuing-education course on practical poultry biosecurity — "
                                    "access control and new-bird quarantine, all-in/all-out management and real "
                                    "two-step cleaning, and pest control plus the honest test of whether a "
                                    "biosecurity measure genuinely works.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "An unrefilled footbath is worthless — here's what actually closes the gap",
                    "sales_subheadline": "3 modules on practical poultry biosecurity — access control, all-in/"
                                          "all-out cycles, and the honest test every measure should pass.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs advising poultry operations on biosecurity\n"
                        "Practitioners investigating a recurring disease problem on a specific farm\n"
                        "Anyone working the existing Poultry series who wants a deeper, checklist-level treatment"
                    ),
                    "not_for": (
                        "Farmers without any veterinary guidance — this is written to support a vet-client "
                        "biosecurity conversation, not replace it"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Poultry biosecurity CE for vets — access control, all-in/all-out cycles, "
                                         "and testing whether measures actually work.",
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
                organization=org, name="Poultry Biosecurity Checklist — Final Exam",
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
                title="Final Exam — Poultry Biosecurity Checklist",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
