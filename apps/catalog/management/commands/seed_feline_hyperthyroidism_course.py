from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifth of the cat-coverage-gap-closing batch, second part (see
# seed_felv_fiv_course.py's header for the batch's overall context).
# Explicitly cross-references seed_feline_ckd_course.py — the same
# diagnostic wrinkle (hyperthyroidism masking kidney disease) is
# central to both courses, matching how the source article itself
# framed the connection.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A benign growth with an outsized effect</h2>
<p>Feline hyperthyroidism is caused by an overactive thyroid, almost always from a benign growth on the gland itself, producing excess thyroid hormone. It's one of the most commonly diagnosed hormonal disorders in older cats.</p>
<h2>Who's affected</h2>
<p>Hyperthyroidism occurs in middle-aged to older cats and is rare in young cats. It's common enough over age 10 to be standard senior-screening bloodwork, right alongside kidney values — a pairing that matters directly for the diagnostic wrinkle covered later in this course.</p>"""),
    ("Clinical Findings",
     """<h2>The classic, counterintuitive sign</h2>
<p>WEIGHT LOSS DESPITE NORMAL OR INCREASED APPETITE is the classic sign of feline hyperthyroidism — genuinely counterintuitive compared to most illness, where appetite typically drops alongside weight. This single pattern is worth remembering as a strong pointer toward hyperthyroidism specifically, distinct from the appetite-loss-plus-weight-loss pattern seen in most other wasting conditions.</p>
<h2>Other signs</h2>
<p>Hyperactivity and restlessness, a fast heart rate, vomiting, increased thirst and urination, and a poor, unkempt coat round out the typical presentation.</p>"""),
    ("Diagnosis — A Genuine Wrinkle",
     """<h2>Usually straightforward — with one real complication</h2>
<p>Bloodwork measuring T4 is usually straightforward for diagnosis. BUT there's a genuine wrinkle worth knowing well: hyperthyroidism can MASK concurrent kidney disease by artificially increasing renal blood flow, so kidney values can look falsely normal in a cat that actually has underlying chronic kidney disease (CKD, covered in its own course on this platform) — until hyperthyroidism treatment normalizes that blood flow and the true kidney picture becomes visible.</p>
<h2>Why this matters practically</h2>
<p>This is the real reason vets re-check kidney function after starting hyperthyroidism treatment — not a routine formality, but a genuine diagnostic necessity given how one disease can hide the other until treatment removes the masking effect.</p>"""),
    ("Treatment",
     """<h2>Several genuinely effective options</h2>
<p>Oral or transdermal medication, given daily and ongoing, controls but doesn't cure hyperthyroidism. An iodine-restricted therapeutic diet works, but requires ONLY that diet with no exceptions to be effective. Radioactive iodine therapy is often curative in a single session, though it needs a licensed facility and an isolation period afterward. Surgical removal of the affected thyroid tissue is less commonly used now, given the effectiveness of the other options.</p>
<h2>Choosing between options</h2>
<p>The right choice depends on concurrent conditions, especially kidney function, given the diagnostic wrinkle covered in the previous module — a cat with underlying kidney disease that hyperthyroidism has been masking needs that factored into the treatment decision, not treated as a separate, later concern.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for an individual cat's treatment choice. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is weight loss despite a normal or increased appetite considered the classic, recognizable sign of feline hyperthyroidism?",
        "It's genuinely counterintuitive compared to most illness, where appetite typically drops alongside "
        "weight — making this specific combination a strong pointer toward hyperthyroidism rather than a general "
        "wasting condition.",
        "It's counterintuitive compared to most illness, where appetite usually drops alongside weight loss",
        "Weight loss with a good appetite is actually the most common pattern across nearly all feline illnesses",
    ),
    (
        "Why can hyperthyroidism cause kidney values to look falsely normal in a cat with underlying CKD?",
        "It artificially increases renal blood flow, which can mask the true kidney picture until treatment "
        "normalizes that blood flow and the underlying kidney disease becomes visible.",
        "It artificially increases renal blood flow, masking underlying kidney disease until treatment normalizes it",
        "Hyperthyroidism has no real effect on kidney values and cannot mask concurrent kidney disease",
    ),
    (
        "Why do vets specifically re-check kidney function after starting hyperthyroidism treatment?",
        "Treatment normalizes the renal blood flow that hyperthyroidism had been artificially increasing, which "
        "can unmask kidney disease that was hidden by falsely normal-looking values beforehand.",
        "Treatment can unmask kidney disease that hyperthyroidism's effect on blood flow had been hiding",
        "This re-check is a routine formality with no real diagnostic purpose behind it",
    ),
    (
        "Why does an iodine-restricted therapeutic diet require strict adherence with no exceptions to be effective?",
        "The diet works specifically by restricting iodine intake as the treatment mechanism itself — any outside "
        "food source reintroduces iodine and can undermine that control, unlike a diet chosen for general benefit.",
        "The diet's effectiveness depends on restricting iodine intake completely, so any outside food undermines it",
        "The iodine-restricted diet works effectively even with occasional exceptions, similar to most dietary changes",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Hyperthyroidism in Cats' — fifth of the cat-coverage-gap-closing "
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
                organization=org, programme=programme, slug="hyperthyroidism-in-cats",
                defaults={
                    "title": "Hyperthyroidism in Cats",
                    "subtitle": "Weight loss despite a normal or increased appetite is the classic sign — and "
                                 "treating it can unmask a kidney problem that was hiding underneath the whole time.",
                    "description": "<p>A 4-module continuing-education course on feline hyperthyroidism — "
                                    "etiology and who's typically affected, the classic counterintuitive weight-"
                                    "loss-with-good-appetite sign, the genuine diagnostic wrinkle with concurrent "
                                    "kidney disease, and choosing among several genuinely effective treatment "
                                    "options.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Treating this can unmask a kidney problem that's been hiding all along",
                    "sales_subheadline": "4 modules on feline hyperthyroidism — the counterintuitive classic "
                                          "sign, the CKD-masking wrinkle, and choosing among real treatment options.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners building senior-cat wellness screening protocols\n"
                        "Anyone who's taken the Feline CKD course and wants the connected diagnostic wrinkle"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline hyperthyroidism CE for vets — the classic sign, the CKD-masking "
                                         "wrinkle, and real treatment options.",
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
                organization=org, name="Hyperthyroidism in Cats — Final Exam",
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
                title="Final Exam — Hyperthyroidism in Cats",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
