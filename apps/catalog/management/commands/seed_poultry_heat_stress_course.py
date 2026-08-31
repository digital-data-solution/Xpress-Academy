from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Seventeenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Why Heat Stress Is a Real Emergency",
     """<h2>Chickens don't sweat</h2>
<p>Chickens cool themselves almost entirely through panting and behavior, since they can't sweat the way mammals do — which is exactly why Nigeria's climate makes this a genuinely high-stakes management issue, not a minor seasonal inconvenience.</p>
<h2>What happens above the thermoneutral zone</h2>
<p>Above the thermoneutral zone, feed intake drops — right when cooling actually needs energy — while water intake rises sharply. Severe cases are directly fatal, especially in high-producing layers and fast-growing broilers, both of which already generate more metabolic heat than a slower-growing or lower-producing bird would.</p>"""),
    ("Recognizing Heat Stress",
     """<h2>Early and severe signs</h2>
<p>Panting, wings held away from the body, reduced activity and feed intake, and increased water consumption are the early signs. Severe cases show labored breathing, weakness, collapse, and death — which can happen fast in dense housing with poor ventilation, leaving little warning window once it starts.</p>
<h2>Production effects even without severe visible signs</h2>
<p>Heat stress reduces egg production and produces THINNER eggshells — heat stress specifically disrupts calcium metabolism, not just general appetite — along with slower broiler growth. These production effects can appear even in birds that never show the severe, dramatic signs described above, which is why production data is worth watching during hot periods even when birds look outwardly fine.</p>"""),
    ("Cooling Measures and Housing Design",
     """<h2>Ventilation is the primary lever</h2>
<p>Airflow removes both heat and moisture, making ventilation the primary tool available — fans, open-sided design, and stocking density all matter here, since overcrowding compounds heat stress directly by trapping more birds' worth of metabolic heat in the same airspace.</p>
<h2>Water, feeding timing, and density adjustments</h2>
<p>Cool water is genuinely more effective than warm water for helping birds cope. Shifting feeding schedules toward cooler hours helps, since digestion itself generates heat. Reducing stocking density in hot seasons and providing electrolyte supplementation during heat waves round out the practical response toolkit.</p>
<h2>Housing design sets the baseline before daily management even starts</h2>
<p>Roof insulation, reflective roofing, eave and ridge ventilation, and building orientation relative to prevailing wind all set a farm's baseline heat exposure before any day-to-day management decision comes into play — genuinely worth factoring into any construction or renovation decision in Nigeria's climate, not just treated as a later add-on.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for a specific operation. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does chickens' inability to sweat make heat stress a genuinely high-stakes issue in Nigeria's climate?",
        "Panting and behavior are almost their entire cooling system, so in a hot climate they have far fewer "
        "physiological tools available to manage excess heat than a mammal that can sweat would.",
        "Panting and behavior are almost their whole cooling system, leaving few other tools to manage excess heat",
        "Chickens actually cool themselves primarily through sweating, similar to most mammals",
    ),
    (
        "Why can thinner eggshells appear during heat stress even without any dramatic clinical signs?",
        "Heat stress specifically disrupts calcium metabolism, not just general appetite — a production effect "
        "that can show up even in birds that never display severe, visibly dramatic heat-stress signs.",
        "Heat stress specifically disrupts calcium metabolism, producing this effect independent of dramatic signs",
        "Thinner eggshells during hot weather are entirely unrelated to heat stress and reflect normal seasonal variation",
    ),
    (
        "Why does overcrowding compound heat stress risk directly, beyond simply being uncomfortable for birds?",
        "It traps more birds' worth of metabolic heat in the same airspace, directly working against ventilation's "
        "ability to remove that heat effectively.",
        "It traps more metabolic heat from more birds in the same airspace, directly undermining ventilation's effect",
        "Stocking density has no real bearing on how effectively a house can be ventilated during hot weather",
    ),
    (
        "Why is housing design (insulation, ventilation layout, orientation) worth factoring into construction decisions specifically, not just daily management?",
        "It sets a farm's baseline heat exposure before any day-to-day management response even comes into play — "
        "a structural factor that daily fan use or water access can't fully compensate for on its own.",
        "It sets the baseline heat exposure a farm faces before any daily management response is even applied",
        "Housing design has a negligible effect on heat stress compared to daily management choices alone",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Heat Stress Management in Poultry' — seventeenth of the poultry-only "
        "~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="poultry-heat-stress-management",
                defaults={
                    "title": "Heat Stress Management in Poultry",
                    "subtitle": "Chickens don't sweat — panting and water are almost their whole cooling system, "
                                 "exactly why Nigeria's climate makes this high-stakes.",
                    "description": "<p>A 3-module continuing-education course on poultry heat stress — why it's a "
                                    "real physiological emergency given how chickens cool themselves, recognizing "
                                    "both severe signs and hidden production effects, and cooling measures plus "
                                    "housing design that sets the baseline before daily management even begins.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Real damage happens even in birds that never show a single dramatic sign",
                    "sales_subheadline": "3 modules on poultry heat stress — recognition, cooling measures, and "
                                          "housing design decisions that set your baseline before summer even starts.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry operations in Nigeria's climate\n"
                        "Practitioners investigating a heat-season production drop\n"
                        "Anyone planning new poultry housing construction or renovation"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Poultry heat stress CE for vets — recognition, cooling measures, and "
                                         "housing design for Nigeria's climate.",
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
                organization=org, name="Heat Stress Management in Poultry — Final Exam",
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
                title="Final Exam — Heat Stress Management in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
