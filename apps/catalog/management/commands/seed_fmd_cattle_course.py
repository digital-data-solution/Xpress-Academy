from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Tenth of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context). No dedicated
# livestock Programme exists yet — placed under Veterinary Continuing
# Education following the same precedent already set by PPR and the
# poultry series (see seed_ppr_goats_sheep_course.py's own header).

MODULES = [
    ("Etiology and a Strain-Matching Problem",
     """<h2>Multiple serotypes, no cross-protection</h2>
<p>Foot-and-mouth disease (FMD) is caused by FMD virus, a picornavirus, with multiple serotypes — O, A, C, SAT1-3, and Asia1. IMMUNITY TO ONE SEROTYPE DOES NOT PROTECT AGAINST ANOTHER. This strain-matching problem is genuinely similar to infectious bronchitis in poultry, already covered in its own course on this platform, but the trade and economic stakes here are far higher.</p>
<h2>Among the most transmissible livestock diseases known</h2>
<p>FMD is among the most transmissible livestock diseases known — spreading via direct contact, aerosol over real distances under the right conditions, contaminated equipment, vehicles, and people, and even animal products. It's genuinely multi-species, affecting cattle, pigs, sheep, and goats, not cattle alone despite the name most commonly associating it with cattle.</p>"""),
    ("Clinical Findings and the Real Cost",
     """<h2>What you'll see</h2>
<p>Fever comes first, followed by vesicles — blisters — on the mouth, tongue, and gums, and around the hooves. These rupture into painful erosions, causing drooling, reluctance to eat, and lameness. Dairy cattle show a sharp milk production drop. At necropsy in fatal young cases, "tiger heart" striping from myocarditis is a distinctive finding.</p>
<h2>Where the real economic damage actually comes from</h2>
<p>Morbidity approaches 100% in susceptible populations. Adult mortality is often low, though young animals can die from myocarditis. The real economic cost is production loss plus trade and movement restrictions, even when direct mortality is modest — worth stating plainly, since the disease's true impact on a farm or a country's export economy isn't well captured by mortality figures alone.</p>"""),
    ("Diagnosis, Treatment, and Control",
     """<h2>Why lab confirmation and serotyping are essential, not optional</h2>
<p>Characteristic vesicular lesions raise suspicion, but LAB CONFIRMATION AND SEROTYPING are essential — other vesicular diseases look similar on presentation, and given the real trade and regulatory implications of an FMD diagnosis, confirmation genuinely changes the response in a way that clinical suspicion alone can't justify. Vesicular stomatitis and other vesicular diseases are the key differentials.</p>
<h2>No treatment — response is about control, not the individual animal</h2>
<p>There is no antiviral treatment; supportive care is all that's available for an individual animal. The response is overwhelmingly about CONTROL, not individual treatment — FMD is notifiable essentially everywhere, and response involves movement restriction, quarantine, and, depending on policy and scale, possible culling. Strict disinfection is standard.</p>
<h2>Prevention — vaccination must match the circulating strain</h2>
<p>Vaccination MUST match the circulating serotype or serotypes — a mismatch produces false confidence, not real protection, echoing the exact strain-matching problem already established for infectious bronchitis in poultry. Biosecurity — movement control, disinfection, quarantine — matters enormously given how many transmission routes are available to this virus.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's or a national veterinary authority's own guidance on an active outbreak. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does immunity to one FMD serotype offer no protection against another serotype?",
        "The multiple serotypes (O, A, C, SAT1-3, Asia1) don't cross-protect one another, meaning a vaccination "
        "or prior infection with one leaves an animal fully susceptible to a different circulating serotype.",
        "The multiple serotypes don't cross-protect one another, leaving prior immunity ineffective against a different one",
        "All FMD serotypes provide full cross-protection against one another once an animal has been exposed to any one",
    ),
    (
        "Why is a vaccine mismatch against the circulating FMD serotype worse than simply not vaccinating at all, in terms of the false confidence it creates?",
        "Vaccination with a mismatched serotype produces false confidence rather than real protection, since the "
        "animal remains susceptible to the actual circulating strain despite appearing vaccinated and protected.",
        "A mismatched vaccine produces false confidence rather than any real protection against the circulating strain",
        "Any FMD vaccine provides equal protection against every circulating serotype regardless of the specific match",
    ),
    (
        "Why is FMD's real economic cost often understated by looking at direct mortality figures alone?",
        "The disease's actual impact comes overwhelmingly from production loss and trade/movement restrictions, "
        "which remain severe even when adult mortality itself stays relatively low.",
        "Production loss and trade/movement restrictions drive the real cost, even with modest direct mortality",
        "FMD's direct mortality rate alone fully captures its true economic impact on a farm or a national economy",
    ),
    (
        "Why is lab confirmation and serotyping considered essential rather than optional once vesicular lesions are seen?",
        "Other vesicular diseases look similar on clinical presentation, and given the real trade and regulatory "
        "implications of an FMD diagnosis, confirmation genuinely changes the response in a way suspicion alone can't.",
        "Other vesicular diseases look clinically similar, and confirmation carries real trade/regulatory consequences",
        "Vesicular lesions are fully diagnostic of FMD on their own, making lab confirmation a redundant formality",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Foot-and-Mouth Disease in Cattle' — tenth of the mixed dogs/cats/"
        "livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="foot-and-mouth-disease-in-cattle",
                defaults={
                    "title": "Foot-and-Mouth Disease in Cattle",
                    "subtitle": "One of the most contagious livestock diseases known, affecting far more than "
                                 "just cattle — and immunity to one strain does nothing against another.",
                    "description": "<p>A 3-module continuing-education course on foot-and-mouth disease — "
                                    "etiology and the serotype-matching problem that has no cross-protection, "
                                    "clinical findings and why the real cost is production loss and trade "
                                    "restrictions rather than mortality alone, and diagnosis/treatment/control "
                                    "centered on lab confirmation and strain-matched vaccination.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Immunity to one strain does absolutely nothing against another",
                    "sales_subheadline": "3 modules on foot-and-mouth disease — serotype mismatch risk, the real "
                                          "trade/production cost, and lab-confirmed, strain-matched control.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving cattle, pig, sheep, and goat operations\n"
                        "Practitioners advising on vaccination programs and trade/movement compliance\n"
                        "Anyone who's taken the Infectious Bronchitis course and wants the livestock parallel"
                    ),
                    "not_for": (
                        "Farmers without veterinary training looking for basic livestock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "FMD CE for vets — serotype mismatch risk, real trade/production cost, "
                                         "and strain-matched control.",
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
                organization=org, name="Foot-and-Mouth Disease in Cattle — Final Exam",
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
                title="Final Exam — Foot-and-Mouth Disease in Cattle",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
