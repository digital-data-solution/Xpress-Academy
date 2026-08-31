from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Sixth of the cat-coverage-gap-closing batch (see
# seed_felv_fiv_course.py's header for the batch's overall context).
# Explicitly cross-references seed_feline_hyperthyroidism_course.py's
# clinical presentation (appetite-plus-weight pattern) to help
# distinguish the two conditions, matching how the source article
# itself framed the comparison.

MODULES = [
    ("Etiology, Epidemiology, and a More Hopeful Picture",
     """<h2>Type 2-like, and genuinely different from canine diabetes</h2>
<p>Feline diabetes mellitus is most commonly Type 2-like — insulin resistance, often obesity-linked — distinct from Type 1 in an important way: some cats achieve REMISSION with good early management. This is a genuinely more hopeful picture than canine diabetes, which is typically a lifelong insulin commitment with no real prospect of remission.</p>
<h2>The single most significant modifiable risk factor</h2>
<p>OBESITY is the single most significant modifiable risk factor for feline diabetes — a large share of feline diabetes cases occur in overweight cats, which is exactly why the prevention module later in this course centers on weight rather than anything more exotic.</p>"""),
    ("Clinical Findings",
     """<h2>The typical presentation</h2>
<p>Increased thirst and urination, increased appetite PAIRED WITH weight loss, and lethargy or weakness make up the typical presentation.</p>
<h2>A pattern worth distinguishing from hyperthyroidism</h2>
<p>This increased-appetite-with-weight-loss pattern is worth explicitly distinguishing from hyperthyroidism's own classic combination — normal or increased appetite with weight loss, covered in its own course on this platform. The two conditions can look superficially similar on a quick read, but the full clinical picture and bloodwork differ meaningfully, and both are genuinely common enough in older cats to be real differentials for each other.</p>
<h2>Advanced or poorly controlled disease</h2>
<p>A distinctive weak, flat-footed rear-leg stance — diabetic neuropathy — appears in advanced or poorly controlled cases, reflecting real nerve damage from sustained high blood sugar.</p>"""),
    ("Diagnosis — a Real Wrinkle",
     """<h2>The basic picture</h2>
<p>Elevated blood glucose combined with glucosuria (glucose in the urine) points toward diabetes.</p>
<h2>Why a single reading can genuinely mislead</h2>
<p>BUT there's a real wrinkle: STRESS ALONE — including the stress of the vet visit itself — can temporarily elevate a cat's blood glucose enough to look diabetic on a single reading. This is a real, well-documented phenomenon in cats specifically, not a minor technicality. Diagnosis relies on multiple readings plus fructosamine, which reflects average blood sugar over the preceding weeks and specifically avoids the stress-driven false positive that a single glucose reading can produce, combined with the clinical signs from the previous module.</p>"""),
    ("Treatment and Prevention",
     """<h2>Insulin and diet together</h2>
<p>Insulin injections, typically given twice daily by the owner after proper training, form the core of treatment, alongside dietary management. A LOW-CARBOHYDRATE diet is specifically recommended — distinct from a general weight-management diet — because carbohydrate content directly affects blood sugar control in cats more directly than in many other conditions where diet plays a supporting role.</p>
<h2>The genuine possibility unique to feline diabetes</h2>
<p>With prompt diagnosis, good early control, and the right diet, some cats achieve remission — sometimes long-term, with insulin no longer needed at all. This genuine possibility, unique among the conditions covered in this batch, is exactly why early, aggressive management is worth pursuing rather than treating a new diagnosis as an automatic lifelong commitment from day one.</p>
<h2>Prevention</h2>
<p>Maintaining a healthy body weight throughout a cat's life is the single most impactful preventive measure, given obesity's outsized role established in the first module.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for an individual cat's insulin protocol. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is feline diabetes mellitus described as offering a more hopeful picture than canine diabetes?",
        "Some cats achieve genuine remission with good early management, unlike canine diabetes, which is "
        "typically a lifelong insulin commitment with no real prospect of remission.",
        "Some cats can achieve genuine remission with good early management, unlike typically lifelong canine diabetes",
        "Feline and canine diabetes carry an identical prognosis and management outlook in essentially every case",
    ),
    (
        "Why can a single elevated blood glucose reading genuinely mislead a diabetes diagnosis in a cat?",
        "Stress alone, including the stress of the vet visit itself, can temporarily elevate glucose enough to "
        "look diabetic on one reading — a real, well-documented phenomenon specific to cats.",
        "Stress alone, including from the vet visit itself, can temporarily elevate glucose enough to look diabetic",
        "Blood glucose readings in cats are never meaningfully affected by stress or the vet visit environment",
    ),
    (
        "Why does fructosamine testing help avoid the false-positive risk that a single glucose reading carries?",
        "It reflects average blood sugar over the preceding weeks rather than a single moment, so a temporary "
        "stress-driven spike doesn't distort the result the way it can with one glucose reading.",
        "It reflects average blood sugar over preceding weeks, avoiding distortion from a single stress-driven spike",
        "Fructosamine testing is exactly as vulnerable to stress-driven false positives as a single glucose reading",
    ),
    (
        "Why is a low-carbohydrate diet specifically recommended for feline diabetes, rather than a general weight-management diet?",
        "Carbohydrate content directly affects blood sugar control in cats more directly than in many other "
        "conditions, making it a targeted treatment lever rather than simply a general health measure.",
        "Carbohydrate content directly affects blood sugar control in cats more directly than a general diet approach",
        "Carbohydrate content has no particular relevance to blood sugar control in diabetic cats specifically",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Diabetes Mellitus' — sixth of the cat-coverage-gap-closing "
        "batch. Safe to re-run."
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
                organization=org, programme=programme, slug="feline-diabetes-mellitus",
                defaults={
                    "title": "Feline Diabetes Mellitus",
                    "subtitle": "Unlike diabetic dogs, some cats can actually go into remission — with prompt "
                                 "diagnosis and good early control, insulin isn't necessarily a lifelong "
                                 "commitment.",
                    "description": "<p>A 4-module continuing-education course on feline diabetes — etiology and "
                                    "the real possibility of remission that distinguishes it from canine "
                                    "diabetes, clinical findings including how to distinguish it from "
                                    "hyperthyroidism, the stress-driven false-positive diagnostic wrinkle, and "
                                    "treatment/prevention centered on early aggressive management.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Insulin isn't necessarily a lifelong commitment — a real possibility unique to cats",
                    "sales_subheadline": "4 modules on feline diabetes — the real remission possibility, "
                                          "distinguishing it from hyperthyroidism, and the stress false-positive trap.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners distinguishing a newly diagnosed diabetic cat from a hyperthyroid one\n"
                        "Anyone counseling owners on early aggressive management toward possible remission"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline diabetes CE for vets — remission possibility, distinguishing it "
                                         "from hyperthyroidism, and the stress false-positive trap.",
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
                organization=org, name="Feline Diabetes Mellitus — Final Exam",
                description="Covers all 4 modules — must be passed to unlock the certificate.",
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
                title="Final Exam — Feline Diabetes Mellitus",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
