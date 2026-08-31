from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Eleventh of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context). Same
# no-dedicated-livestock-Programme precedent as FMD and PPR.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A tsetse-borne parasite with a real geographic story</h2>
<p>Trypanosomiasis in livestock is caused by Trypanosoma protozoan parasites — T. vivax, T. congolense, and T. brucei are most significant in African livestock — transmitted primarily by tsetse flies (Glossina), though mechanical transmission by other biting flies also occurs. That mechanical route matters practically: tsetse-free areas aren't necessarily trypanosomiasis-free.</p>
<h2>A disease that has shaped land use itself</h2>
<p>This is a defining disease of sub-Saharan Africa, including significant parts of Nigeria. Tsetse distribution, linked to vegetation and habitat, has historically shaped entire regional livestock economies and land use — tsetse-infested areas have often been effectively unusable for cattle without active control, a genuinely different scale of impact from most diseases covered on this platform. Cattle, sheep, and goats are all affected, though cattle suffer the most severe economic impact.</p>"""),
    ("Clinical Findings",
     """<h2>Usually chronic, not dramatic</h2>
<p>The disease is chronic and progressive: intermittent fever, progressive ANEMIA — the hallmark finding — weight loss and poor body condition despite adequate feed, reduced fertility or abortion, reduced milk, and enlarged lymph nodes.</p>
<h2>The presentation most worth remembering</h2>
<p>Trypanosomiasis can be fatal with virulent strains, or in stressed or malnourished animals — but more commonly it presents as chronic unthriftiness: an animal that just never does well, without any single dramatic sign pointing clearly toward this diagnosis. This chronic, unremarkable presentation is exactly why it's worth actively investigating in an underperforming herd in an endemic area, rather than waiting for a more obvious sign that may never come.</p>"""),
    ("Diagnosis, Treatment, and Control",
     """<h2>Diagnosis — a real sensitivity limitation</h2>
<p>Microscopic examination of blood or lymph node aspirate is the traditional standard, though it has limited sensitivity in chronic, low-parasitemia cases — exactly the presentation most likely to be missed by this method. PCR is more sensitive. PCV, measuring anemia, is a practical field indicator even before a specific parasite identification is made, useful as an early flag in a suspicious herd.</p>
<h2>Treatment and a growing resistance concern</h2>
<p>Trypanocidal drugs are widely used, but DRUG RESISTANCE is a real, growing concern from repeated or inappropriate use — veterinary guidance genuinely matters here, not just for treatment efficacy in the moment but for slowing resistance development across the wider population.</p>
<h2>Vector control — a major, distinct lever</h2>
<p>Tsetse fly control — traps, targets, insecticide-treated cattle, area-wide programs — is a major, genuinely effective lever that addresses the VECTOR directly, distinct from treating already-infected animals. Trypanotolerant breeds, certain West African cattle breeds, show real natural resistance, a genuine breed-selection option worth discussing in high-risk areas. Effective prevention combines vector control, tolerant breeds, and sometimes prophylactic treatment in high-risk areas or seasons.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for a specific herd. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why isn't a tsetse-free area necessarily a trypanosomiasis-free area?",
        "Mechanical transmission by other biting flies also occurs, alongside the primary tsetse-fly route — so "
        "the absence of tsetse flies alone doesn't guarantee the absence of transmission.",
        "Mechanical transmission by other biting flies means the disease can spread even without tsetse flies present",
        "Trypanosomiasis transmission occurs exclusively through tsetse flies, with no alternative transmission route",
    ),
    (
        "Why should trypanosomiasis be actively considered in an underperforming herd, even without a single dramatic sign?",
        "The most common presentation is chronic unthriftiness — an animal that just never does well — rather "
        "than a single obvious symptom that would otherwise point clearly toward the diagnosis.",
        "The most common presentation is chronic unthriftiness with no single dramatic sign, easy to overlook otherwise",
        "Trypanosomiasis nearly always presents with an unmistakable, dramatic clinical picture in affected animals",
    ),
    (
        "Why does microscopic examination have a real limitation specifically in chronic, low-parasitemia cases?",
        "Its sensitivity drops in exactly this scenario — chronic, low-parasitemia infection — which happens to be "
        "the presentation most likely to be missed by this traditional standard diagnostic method.",
        "Its sensitivity is limited in chronic, low-parasitemia cases, the exact presentation most likely to be missed",
        "Microscopic examination is equally sensitive across every stage and parasite level of infection",
    ),
    (
        "Why is tsetse fly control considered a distinct, major lever from treating infected animals with trypanocidal drugs?",
        "It addresses the vector itself rather than individual infected animals, directly reducing new transmission "
        "at a scale that drug treatment of already-infected animals alone can't achieve.",
        "It addresses the vector directly, reducing new transmission rather than only treating already-infected animals",
        "Vector control and drug treatment address the exact same mechanism and produce interchangeable results",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Trypanosomiasis in Livestock' — eleventh of the mixed dogs/cats/"
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
                organization=org, programme=programme, slug="trypanosomiasis-in-livestock",
                defaults={
                    "title": "Trypanosomiasis in Livestock",
                    "subtitle": "A tsetse-borne disease that has shaped land use and livestock economics across "
                                 "sub-Saharan Africa for generations — usually showing up as chronic "
                                 "unthriftiness, not dramatic outbreaks.",
                    "description": "<p>A 3-module continuing-education course on livestock trypanosomiasis — "
                                    "etiology and the tsetse vector's real regional economic impact, clinical "
                                    "findings emphasizing chronic unthriftiness over dramatic presentation, and "
                                    "diagnosis/treatment/control centered on vector control alongside drug "
                                    "treatment given real resistance concerns.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "An underperforming herd with no obvious sign? Consider this before ruling it out",
                    "sales_subheadline": "3 modules on livestock trypanosomiasis — chronic presentation, "
                                          "diagnosis limits, and vector control alongside real resistance concerns.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving cattle, sheep, and goat operations\n"
                        "Practitioners investigating an underperforming herd in a tsetse-endemic area\n"
                        "Anyone advising on trypanotolerant breed selection or vector control programs"
                    ),
                    "not_for": (
                        "Farmers without veterinary training looking for basic livestock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Livestock trypanosomiasis CE for vets — chronic unthriftiness, "
                                         "diagnosis limits, and vector control alongside resistance concerns.",
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
                organization=org, name="Trypanosomiasis in Livestock — Final Exam",
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
                title="Final Exam — Trypanosomiasis in Livestock",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
