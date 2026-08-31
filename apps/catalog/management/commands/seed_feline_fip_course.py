from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourth of the cat-coverage-gap-closing batch (see
# seed_felv_fiv_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A common, harmless virus that occasionally mutates</h2>
<p>Feline infectious peritonitis (FIP) is caused by feline coronavirus (FCoV) — a virus that's extremely common and usually mild or entirely harmless, especially in multi-cat households. FIP develops when this common virus MUTATES within an individual infected cat into a more aggressive, systemic form. This is worth stating precisely: FIP itself isn't "caught" directly from another cat with FIP — it develops from a mutation of ordinary coronavirus already present in that specific cat.</p>
<h2>Who's actually at higher risk</h2>
<p>Young cats, particularly under two years old, and cats in multi-cat environments like shelters and catteries, face higher risk — both because FCoV is simply more prevalent in crowded populations, and because stress or a developing immune system may increase the likelihood of the mutation itself occurring.</p>"""),
    ("Clinical Findings",
     """<h2>Two forms, different presentations</h2>
<p>The "wet" or effusive form causes fluid accumulation in the abdomen or chest, producing a distended abdomen or labored breathing. The "dry" or non-effusive form produces granulomatous lesions in various organs — eyes, brain, kidneys, liver — with signs varying by which organ is affected, including neurological signs, eye inflammation, and organ dysfunction.</p>
<h2>What both forms share</h2>
<p>Both forms typically also cause antibiotic-unresponsive fever, lethargy, and weight loss — a persistent fever that doesn't respond to antibiotics is itself a real clue worth taking seriously in a young cat, particularly one from a multi-cat environment.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>A genuinely challenging diagnosis, built from a pattern</h2>
<p>There is no single perfect test for FIP. Fluid analysis (for the wet form), characteristic bloodwork patterns, and PCR all contribute to a presumptive diagnosis built from a combination of findings, plus ruling out other causes — rather than any one definitive test settling the question on its own.</p>
<h2>The single most important update in this course</h2>
<p>FIP was, until recently, essentially universally fatal. THE EMERGENCE OF EFFECTIVE ANTIVIRAL TREATMENT — GS-441524 and related compounds — has turned FIP into a treatable, often curable disease, with real sustained response rates when treatment is started and completed properly. Access and regulatory status vary by country, and treatment is genuinely involved — weeks of daily medication with ongoing monitoring — so it's worth confirming current, region-specific options directly with a vet rather than assuming treatment is unavailable based on FIP's old reputation. This single fact changes the entire conversation with an owner facing a suspected FIP diagnosis.</p>
<h2>Prevention</h2>
<p>No broadly recommended vaccine exists. Reducing overcrowding and stress, along with good litter hygiene — FCoV spreads fecal-oral — reduce transmission generally, though they can't eliminate risk entirely given how common the underlying virus already is in most cat populations.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment, particularly given how genuinely difficult FIP diagnosis and treatment access can be. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is it inaccurate to say a cat 'caught FIP' directly from another cat that has FIP?",
        "FIP develops from a mutation of ordinary feline coronavirus already present within an individual "
        "infected cat — it isn't transmitted directly as FIP itself from cat to cat.",
        "FIP develops from a mutation of FCoV already present in that specific cat, not direct FIP-to-FIP transmission",
        "FIP spreads directly between cats in exactly the same way as ordinary feline coronavirus itself",
    ),
    (
        "Why is FIP diagnosis genuinely challenging compared to many other conditions covered on this platform?",
        "There's no single perfect test — diagnosis relies on combining fluid analysis, bloodwork patterns, and "
        "PCR into a presumptive picture built from multiple findings, rather than one definitive result.",
        "No single perfect test exists, so diagnosis relies on combining multiple findings into a presumptive picture",
        "A single definitive blood test reliably confirms or rules out FIP in essentially every suspected case",
    ),
    (
        "Why does the availability of effective antiviral treatment fundamentally change how an FIP diagnosis should be handled today?",
        "FIP was until recently essentially universally fatal, but real antiviral treatment with sustained "
        "response rates now exists — an outdated assumption of automatic death sentence is no longer accurate.",
        "Real antiviral treatment with sustained response rates now exists, unlike FIP's old, essentially fatal reputation",
        "Treatment options for FIP remain exactly as limited today as they were before antiviral options emerged",
    ),
    (
        "Why do young cats and crowded multi-cat environments carry higher FIP risk?",
        "FCoV is simply more prevalent in crowded populations, and stress or a developing immune system may "
        "increase the likelihood of the mutation that actually produces FIP occurring in the first place.",
        "FCoV is more prevalent in crowded populations, and stress may increase the likelihood of the FIP-causing mutation",
        "Young cats and crowded environments actually carry a lower FIP risk than isolated adult cats",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Infectious Peritonitis (FIP)' — fourth and final of the "
        "cat-coverage-gap-closing batch's first part. Safe to re-run."
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
                organization=org, programme=programme, slug="feline-infectious-peritonitis-fip",
                defaults={
                    "title": "Feline Infectious Peritonitis (FIP)",
                    "subtitle": "Once considered an almost certain death sentence — real, effective antiviral "
                                 "treatment now exists, and that fact alone is worth knowing before assuming "
                                 "otherwise.",
                    "description": "<p>A 3-module continuing-education course on FIP — etiology and how a common, "
                                    "usually harmless virus occasionally mutates into a fatal disease, clinical "
                                    "findings across the wet and dry forms, and diagnosis/treatment/prevention "
                                    "centered on the real emergence of effective antiviral treatment.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "No longer the automatic death sentence its reputation still suggests",
                    "sales_subheadline": "3 modules on FIP — the mutation mechanism, the wet/dry clinical "
                                          "picture, and the real antiviral treatment now changing outcomes.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners counseling an owner facing a suspected FIP diagnosis\n"
                        "Anyone serving shelters or multi-cat catteries with elevated FCoV exposure"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "FIP CE for vets — the FCoV mutation mechanism, wet/dry clinical "
                                         "presentations, and real antiviral treatment options.",
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
                organization=org, name="Feline Infectious Peritonitis (FIP) — Final Exam",
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
                title="Final Exam — Feline Infectious Peritonitis (FIP)",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
