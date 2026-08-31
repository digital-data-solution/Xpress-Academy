from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Third of the cat-coverage-gap-closing batch (see
# seed_felv_fiv_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Gradual, irreversible, and extremely common</h2>
<p>Chronic kidney disease (CKD) is a gradual, irreversible loss of kidney function over months to years — one of the most common conditions in older cats, and a leading cause of senior-cat illness and death. The underlying cause is often never identified; when it is known, chronic infection, high blood pressure, toxins, and breed-linked genetic conditions such as polycystic kidney disease in Persians and related breeds are among the possibilities.</p>
<h2>Less "if" than "when" for a genuinely elderly cat</h2>
<p>Prevalence rises sharply with age — a substantial share of cats over 15 show some degree of CKD, making this genuinely less a question of "if" and more a question of "when" for a truly elderly cat, a framing worth adopting for senior-cat wellness conversations generally.</p>"""),
    ("Clinical Findings — The Central Challenge",
     """<h2>Why signs appear so late</h2>
<p>Because of the kidney's reserve capacity, clinical signs don't appear until substantial function is already lost. Increased thirst and urination — reflecting a loss of concentrating ability — weight loss, reduced appetite, and a poor coat appear first, with vomiting, lethargy, and bad breath from toxin buildup appearing in more advanced disease.</p>
<h2>The central challenge of this whole disease</h2>
<p>THIS DELAYED-SYMPTOM PATTERN IS THE CENTRAL CHALLENGE of feline CKD: by the time an owner actually notices something's wrong, real kidney function is often already substantially gone. This single fact is exactly why the diagnosis and prevention modules that follow emphasize routine screening over waiting for signs to appear.</p>"""),
    ("Diagnosis, Treatment, and Early Detection",
     """<h2>Building the diagnosis</h2>
<p>Bloodwork — creatinine plus the newer, earlier-detecting SDMA marker — combined with urinalysis (assessing concentrating ability) and, increasingly, blood pressure measurement together build the diagnosis. CKD and hypertension often co-occur and worsen each other, which is why blood pressure is increasingly checked alongside kidney values rather than treated as a separate concern. A widely used staging system guides treatment and prognosis once CKD is confirmed.</p>
<h2>No cure, but genuinely effective management</h2>
<p>There is no cure, but management genuinely slows progression: therapeutic kidney diets — reduced but higher-quality protein and phosphorus — are the mainstay. Blood pressure management if elevated, anemia management if present (the kidneys also produce a hormone that drives red blood cell production, so kidney disease can cause anemia through a second mechanism beyond the kidney damage itself), and fluid support — including subcutaneous fluids given at home in advanced cases — round out real management.</p>
<h2>Why the priority is early detection, not prevention</h2>
<p>No reliable prevention exists, given how often no specific cause is ever found. The priority instead shifts to EARLY DETECTION: routine senior bloodwork, starting annually from around 7-10 years of age, catches CKD earlier than waiting for signs — at exactly the point where management has the most impact, tying directly back to the delayed-symptom challenge covered in the previous module.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why don't clinical signs of feline CKD appear until substantial kidney function is already lost?",
        "The kidney has real reserve capacity, so noticeable signs like increased thirst and urination only "
        "emerge once that reserve is significantly depleted, well after the disease process actually began.",
        "The kidney's reserve capacity means signs only emerge once that reserve is substantially depleted",
        "Clinical signs of CKD typically appear very early, well before any meaningful kidney function is lost",
    ),
    (
        "Why does the priority for feline CKD shift to early detection rather than prevention?",
        "No reliable prevention exists given how often a specific cause is never identified, so routine senior "
        "screening is what actually catches the disease at the point where management still has real impact.",
        "No reliable prevention exists, so routine senior screening is the practical way to catch it early instead",
        "Feline CKD is fully preventable with proper diet and lifestyle management from an early age",
    ),
    (
        "Why are blood pressure and kidney values increasingly checked together rather than as separate concerns?",
        "CKD and hypertension often co-occur and worsen each other, so checking one without the other risks "
        "missing a compounding factor that's actively making the disease harder to manage.",
        "CKD and hypertension often co-occur and worsen each other, making them worth checking together",
        "Blood pressure has no meaningful connection to kidney disease progression in cats specifically",
    ),
    (
        "Why can a cat with CKD develop anemia through a mechanism separate from the kidney damage itself?",
        "The kidneys also produce a hormone that drives red blood cell production, so kidney disease can cause "
        "anemia through loss of that hormone function, not only through the direct kidney damage.",
        "The kidneys produce a hormone driving red blood cell production, and its loss can cause anemia on its own",
        "Anemia in feline CKD results exclusively from direct kidney tissue damage, with no other contributing mechanism",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Chronic Kidney Disease' — third of the cat-coverage-gap-"
        "closing batch. Safe to re-run."
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
                organization=org, programme=programme, slug="feline-chronic-kidney-disease",
                defaults={
                    "title": "Feline Chronic Kidney Disease",
                    "subtitle": "By the time a cat shows obvious symptoms, real kidney function is often "
                                 "already gone — exactly why routine senior bloodwork matters more than waiting "
                                 "to notice something's wrong.",
                    "description": "<p>A 3-module continuing-education course on feline CKD — etiology and why "
                                    "prevalence is nearly universal in genuinely elderly cats, the delayed-"
                                    "symptom pattern that's the disease's central diagnostic challenge, and "
                                    "diagnosis/treatment centered on early detection through routine senior "
                                    "screening.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "By the time an owner notices, real kidney function is often already gone",
                    "sales_subheadline": "3 modules on feline CKD — the delayed-symptom challenge, staging and "
                                          "management, and why early senior screening matters most.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners building a senior-cat wellness screening protocol\n"
                        "Anyone managing a newly diagnosed CKD case and weighing therapeutic-diet options"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline CKD CE for vets — delayed-symptom challenge, staging and "
                                         "management, and early senior screening.",
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
                organization=org, name="Feline Chronic Kidney Disease — Final Exam",
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
                title="Final Exam — Feline Chronic Kidney Disease",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
