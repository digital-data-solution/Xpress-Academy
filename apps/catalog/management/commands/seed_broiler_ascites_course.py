from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Eighteenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Written
# alongside seed_broiler_sudden_death_syndrome_course.py — both are
# consequences of broiler growth outpacing cardiovascular capacity,
# and each course explicitly contrasts against the other's different
# mechanism and presentation, matching how the two articles themselves
# were framed together.

MODULES = [
    ("What's Actually Happening",
     """<h2>A race the cardiovascular system loses</h2>
<p>Ascites syndrome — "water belly" — strikes the biggest, fastest-growing birds in a flock. Extremely rapid growth demands a proportionally large oxygen supply, and the cardiovascular and pulmonary system simply can't keep pace with modern broilers' growth rate. The result is pulmonary hypertension, right-sided heart failure, and abdominal fluid accumulation.</p>
<h2>What worsens the underlying mismatch</h2>
<p>Cold brooding raises metabolic and oxygen demand at exactly the wrong time. High altitude means lower ambient oxygen — a genuine consideration in Nigeria's plateau and highland regions, not a theoretical concern. Poor ventilation and high ammonia reduce effective oxygen availability and damage lung tissue directly, compounding the problem from two directions at once.</p>"""),
    ("Risk Factors and Clinical Findings",
     """<h2>Counterintuitively, the best-performing birds are most at risk</h2>
<p>Fast early growth, cold brooding temperatures, high altitude, poor ventilation and ammonia buildup, and rapid early feed intake from high-energy starter diets are the recognized risk factors. The counterintuitive part is worth stating plainly: the BEST-performing birds are most at risk, not the weakest ones — this is a genuine growth-rate problem, not a health-weakness problem.</p>
<h2>What you'll see</h2>
<p>Affected birds are often the LARGEST, best-grown birds in the flock — not runts, which is exactly why ascites can catch a farm off guard. A distended, fluid-filled abdomen ("water belly"), lethargy, reluctance to move, labored breathing, and a cyanotic (bluish) comb or skin are the visible signs. Sudden death is common, often with minimal preceding signs.</p>"""),
    ("Diagnosis and Management",
     """<h2>A recognizable clinical picture</h2>
<p>History — a fast-growing broiler, altitude, cold brooding, or poor ventilation — combined with necropsy findings of ascitic fluid and right heart enlargement is usually sufficient. Lesions include clear-to-straw abdominal fluid, an enlarged, flabby right heart (right ventricular hypertrophy), congested and edematous lungs, and, in chronic cases, an enlarged, congested liver.</p>
<h2>Prevention, not treatment</h2>
<p>There is no treatment for an individual affected bird — cull on welfare grounds. Prevention is where the real work happens: careful brooding temperature management to avoid the cold stress that raises oxygen demand, adequate ventilation especially as birds approach their heaviest weight, feeding programs that moderate the earliest growth rate (a real tradeoff against maximum speed, worth a deliberate decision rather than a default), and genetics — some strains are more susceptible than others.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for a specific operation. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is ascites syndrome fundamentally a growth-rate problem rather than a typical infectious disease?",
        "It results from extremely rapid growth demanding oxygen faster than the cardiovascular and pulmonary "
        "system can keep pace with — a mismatch, not a pathogen infecting the bird.",
        "It results from rapid growth outpacing the cardiovascular system's oxygen supply capacity, not infection",
        "It's caused by a specific bacterial pathogen that targets fast-growing broilers preferentially",
    ),
    (
        "Why is high altitude a genuine risk factor for ascites in Nigeria specifically, not just a theoretical concern?",
        "Nigeria has real plateau and highland regions where lower ambient oxygen at altitude compounds the "
        "oxygen-supply mismatch already driving ascites at sea level.",
        "Nigeria has real plateau/highland regions where lower ambient oxygen compounds the underlying oxygen mismatch",
        "Altitude has no real bearing on ascites risk anywhere, including Nigeria's highland regions",
    ),
    (
        "Why is it counterintuitive that the best-performing broilers are most at risk for ascites?",
        "Ascites is driven by growth rate outpacing cardiovascular capacity, so the fastest-growing, "
        "best-performing birds are actually the ones most exposed to that underlying mismatch — not the weakest ones.",
        "The fastest-growing birds are most exposed to the growth-outpacing-cardiovascular-capacity mismatch",
        "Slower-growing, poorly-performing birds are consistently the ones most at risk for ascites",
    ),
    (
        "Why does moderating a broiler's earliest growth rate represent a real tradeoff rather than a simple fix?",
        "It reduces ascites risk but works against the goal of maximum growth speed, so it's a deliberate "
        "management decision weighing production speed against cardiovascular risk — not a cost-free adjustment.",
        "It reduces ascites risk but works directly against the goal of achieving maximum possible growth speed",
        "Moderating early growth rate has no real effect on either ascites risk or overall production speed",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Ascites Syndrome in Broilers' — eighteenth of the poultry-only "
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
                organization=org, programme=programme, slug="ascites-syndrome-in-broilers",
                defaults={
                    "title": "Ascites Syndrome in Broilers",
                    "subtitle": "\"Water belly\" strikes the biggest, fastest-growing birds in the flock — a "
                                 "broiler's heart and lungs losing the race against its own growth rate.",
                    "description": "<p>A 3-module continuing-education course on broiler ascites syndrome — the "
                                    "growth-versus-cardiovascular-capacity mismatch and what worsens it, risk "
                                    "factors including the counterintuitive best-performer risk pattern, and "
                                    "diagnosis/management centered on prevention through brooding, ventilation, "
                                    "and growth-rate decisions.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Your best-performing birds are the ones actually most at risk here",
                    "sales_subheadline": "3 modules on broiler ascites — the growth/cardiovascular mismatch, real "
                                          "risk factors, and prevention through brooding and ventilation decisions.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving broiler operations\n"
                        "Practitioners investigating unexplained mortality in the best-grown birds in a flock\n"
                        "Anyone working in Nigeria's plateau/highland regions where altitude compounds this risk"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Broiler ascites CE for vets — cardiovascular mismatch, risk factors, and "
                                         "prevention through brooding and ventilation.",
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
                organization=org, name="Ascites Syndrome in Broilers — Final Exam",
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
                title="Final Exam — Ascites Syndrome in Broilers",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
