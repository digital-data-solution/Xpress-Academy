from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Thirteenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Builds
# directly on the cecal worm/histomoniasis link introduced in
# seed_poultry_helminthiasis_course.py — best value taken alongside
# that course, though each stands alone.

MODULES = [
    ("Etiology and an Unusual Transmission Chain",
     """<h2>A protozoan that travels inside a worm's eggs</h2>
<p>Histomoniasis, or blackhead disease, is caused by the protozoan Histomonas meleagridis. Its transmission depends on an unusual chain: the eggs of the cecal worm Heterakis gallinarum carry the protozoan, and earthworms that have eaten Heterakis eggs can transmit it too — a genuine multi-host chain, not a simple direct spread between birds.</p>
<h2>Why this makes worm control disease control</h2>
<p>This transmission route is the single most important practical fact about histomoniasis: because the protozoan travels via Heterakis eggs, deworming for cecal worms is itself an effective, if indirect, control measure — covered in more depth in this platform's Helminthiasis course.</p>"""),
    ("Epidemiology and Clinical Findings",
     """<h2>Turkeys and chickens play very different roles</h2>
<p>Turkeys are dramatically more susceptible than chickens, with much higher mortality. Chickens frequently carry the infection mild or entirely asymptomatic while still shedding the protozoan via Heterakis eggs — which means mixed turkey-chicken operations carry a specific, well-documented risk: the chickens act as a largely silent reservoir infecting the much more vulnerable turkeys.</p>
<h2>Why this is so hard to eliminate once established</h2>
<p>Heterakis eggs remain infective in soil for YEARS. This single fact explains why histomoniasis, once established on a piece of ground, is genuinely difficult to eliminate through short-term measures alone.</p>
<h2>What you'll see</h2>
<p>Depression, drooping wings, and sulfur-yellow droppings are common. In turkeys, cyanotic ("blackhead") discoloration of the head can appear — but it's an inconsistent sign, not something to rely on alone for diagnosis. Mortality is high in turkeys, much lower in chickens.</p>"""),
    ("Diagnosis, Treatment, and Control",
     """<h2>Lesions distinctive enough to diagnose on their own</h2>
<p>Characteristic "target lesions" — circular, necrotic, bullseye-shaped lesions in the liver — are often distinctive enough alone at necropsy. Cecal inflammation, thickening, and ulceration are also seen, sometimes producing a "cecal core," a necrotic cast filling the cecum. Microscopic identification and PCR provide confirmation where needed. Coccidiosis is a key differential worth considering, and can co-occur.</p>
<h2>A real limitation on treatment today</h2>
<p>Historically effective drugs for histomoniasis have been withdrawn or banned in many countries over food-safety and residue concerns. This genuinely limits active-outbreak treatment options today — which is exactly why prevention is disproportionately important for this disease, not a secondary consideration.</p>
<h2>Prevention — separation and worm control</h2>
<p>Do NOT raise turkeys and chickens together, or in sequence on the same ground, without a real gap — given the years-long soil persistence of Heterakis eggs, "real gap" means years, not weeks. Deworming cecal worms is an indirect but genuinely effective control measure, since it removes the vector itself.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does deworming for cecal worms (Heterakis gallinarum) count as effective histomoniasis control?",
        "Histomonas meleagridis transmission depends on Heterakis eggs (and earthworms that ate them) — removing "
        "the worm removes the vector the protozoan relies on to spread.",
        "The protozoan's transmission chain relies on Heterakis eggs, so removing the worm removes its vector",
        "Deworming has no real effect on histomoniasis transmission, which spreads independently of worm burden",
    ),
    (
        "Why do mixed turkey-chicken operations carry a specific, well-documented histomoniasis risk?",
        "Chickens frequently carry the infection mild or asymptomatic while still shedding it via Heterakis eggs, "
        "acting as a largely silent reservoir that infects the much more susceptible turkeys.",
        "Chickens often carry the infection asymptomatically while still shedding it, silently exposing turkeys",
        "Chickens are equally susceptible to severe disease as turkeys, so mixing them doesn't add extra risk",
    ),
    (
        "Why is histomoniasis so difficult to eliminate from a piece of ground once it's established there?",
        "Heterakis eggs remain infective in soil for years, so a short-term gap between flocks isn't enough to "
        "break the transmission cycle on that same ground.",
        "Heterakis eggs remain infective in soil for years, so only a genuinely long gap actually breaks the cycle",
        "Once established, histomoniasis in soil naturally loses infectivity within a few weeks at most",
    ),
    (
        "Why is prevention described as disproportionately important for histomoniasis specifically?",
        "Historically effective treatment drugs have been withdrawn or banned in many countries over food-safety "
        "concerns, genuinely limiting what can be done once an active outbreak is already underway.",
        "Treatment options have been genuinely limited by drug withdrawals, making prevention the more realistic priority",
        "Treatment for histomoniasis remains fully available and effective, making prevention a lower priority",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Histomoniasis (Blackhead Disease) in Poultry' — thirteenth of the "
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
                organization=org, programme=programme, slug="histomoniasis-blackhead-disease",
                defaults={
                    "title": "Histomoniasis (Blackhead Disease) in Poultry",
                    "subtitle": "A parasite that travels inside a worm's eggs — chickens rarely get sick but "
                                 "quietly infect the turkeys sharing their range.",
                    "description": "<p>A 3-module continuing-education course on histomoniasis — etiology and the "
                                    "unusual worm-mediated transmission chain, epidemiology explaining why mixed "
                                    "turkey-chicken operations carry real risk, and diagnosis/treatment/prevention "
                                    "centered on separation and cecal worm control given real treatment "
                                    "limitations today.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Chickens rarely get sick — but they quietly infect the turkeys nearby",
                    "sales_subheadline": "3 modules on histomoniasis — the worm-mediated transmission chain, mixed-"
                                          "species risk, and why prevention matters more than treatment here.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving mixed poultry/turkey operations\n"
                        "Practitioners advising on species separation and cecal worm control\n"
                        "Anyone who's taken the Helminthiasis course and wants the direct connection"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Histomoniasis CE for vets — worm-mediated transmission, mixed-species "
                                         "risk, and separation-based prevention.",
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
                organization=org, name="Histomoniasis (Blackhead Disease) — Final Exam",
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
                title="Final Exam — Histomoniasis (Blackhead Disease)",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
