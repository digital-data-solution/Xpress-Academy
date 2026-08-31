from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Sixth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Deepens
# the brief Marek's coverage inside the existing "Common Viral
# Diseases: Newcastle, Avian Influenza, IBD, Marek's" module in the
# earlier Poultry Health & Biosecurity course — same relationship
# already established elsewhere in this batch. Note on the title's
# apostrophe: verified Django's autoescape handles it safely across
# every template that renders course.title in this codebase (no raw
# JS string interpolation anywhere) — flagged by vetfresh-6c after it
# caused a real bug on the Vet dashboard's own (different) stack.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A herpesvirus with genuine tumor-causing potential</h2>
<p>Marek's disease virus (MDV, Gallid alphaherpesvirus 2) is highly cell-associated — except in the feather follicle epithelium, where it replicates and sheds as fully infectious, environmentally stable particles in skin dander. This is the actual transmission route, and it's what makes Marek's disease extremely widespread: those shed particles survive over a year in the right conditions.</p>
<h2>Why exposure timing is the central fact of this disease</h2>
<p>Transmission is via inhalation of contaminated dander and dust. Exposure often happens very early in life, well before disease is apparent — exactly why vaccination timing, at or before hatch, matters as much as it does. Everything in the prevention module of this course flows from this single epidemiological fact.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>Four distinct presentations</h2>
<p>The classical (neural) form causes progressive paralysis, including the classic "splits" posture — one leg forward, one back — from asymmetric peripheral nerve damage. The visceral form produces lymphomas in the liver, spleen, gonads, kidney, heart, and lungs, with depression, weight loss, or sudden death. The ocular form causes a grey, discolored iris ("grey eye") and an irregular pupil, which can progress to blindness. The skin form produces nodules at feather follicles.</p>
<h2>What each form looks like at necropsy</h2>
<p>The neural form shows enlarged, grey, swollen peripheral nerves that have lost their normal cross-striation. The visceral form shows lymphomatous infiltration or nodules, with liver and spleen enlargement — findings that raise an important differential covered in the next module.</p>"""),
    ("Diagnosis",
     """<h2>Why histopathology is genuinely necessary here, not optional</h2>
<p>Distinguishing Marek's disease from avian leukosis on gross findings alone isn't reliable enough — histopathology is genuinely necessary. Marek's disease shows a T-cell, pleomorphic pattern; avian leukosis shows a B-cell, uniform pattern. This distinction matters clinically, not just academically, since the two diseases have different implications for flock management.</p>
<h2>Confirming and ruling out</h2>
<p>PCR confirms the presence of the virus itself. Key differentials: avian leukosis (the main one, distinguished as above), reticuloendotheliosis, and nutritional or toxic causes of neurological signs.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>No treatment, and a real welfare decision once signs appear</h2>
<p>There is no treatment. The disease is progressive once clinical signs appear, and culling on welfare grounds is the appropriate response at that point.</p>
<h2>The single most important thing to understand about the vaccine</h2>
<p>Vaccinated birds can still become infected and shed the virus — vaccination doesn't eliminate MDV from a flock or a site. What it does is prevent the disease and the tumors that follow from that infection. This is a genuinely different relationship between vaccine and pathogen than most diseases on this platform, and worth stating plainly to avoid a false sense that vaccination has "cleared" a flock.</p>
<h2>Why vaccination timing is non-negotiable</h2>
<p>Vaccination is given at the hatchery — in ovo or subcutaneously on the day of hatch — because natural exposure can happen very early, and post-exposure vaccination gives little to no benefit. HVT is the most common vaccine serotype, sometimes combined with others for stronger protection against virulent strains. Biosecurity and litter management still matter despite vaccination not stopping shedding, since reducing overall viral load in the environment remains worthwhile even in a vaccinated flock.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does Marek's disease vaccination need to happen at or before hatch, rather than at any convenient later point?",
        "Natural exposure to MDV can happen very early in life, and post-exposure vaccination gives little to no "
        "benefit — so vaccination timing has to precede real-world exposure to actually work.",
        "Natural exposure often happens very early, and vaccinating after exposure gives little to no benefit",
        "Vaccination timing has no real effect on how well the Marek's disease vaccine works",
    ),
    (
        "What does it mean that Marek's disease vaccination prevents disease but not infection?",
        "A vaccinated bird can still become infected and shed the virus — the vaccine prevents the disease and "
        "tumors that follow, but doesn't eliminate MDV from the flock or the site.",
        "Vaccinated birds can still become infected and shed virus, even though they don't develop disease",
        "Vaccination fully clears MDV from a flock, preventing both infection and disease entirely",
    ),
    (
        "Why is histopathology genuinely necessary to distinguish Marek's disease from avian leukosis, rather than relying on gross findings alone?",
        "The two diseases show different cellular patterns (T-cell, pleomorphic for Marek's vs. B-cell, uniform for "
        "leukosis) that only histopathology reliably reveals, and the distinction has real management implications.",
        "The two conditions show distinct cellular patterns under histopathology that gross exam alone can't reliably tell apart",
        "Gross necropsy findings alone are always sufficient to reliably distinguish the two conditions",
    ),
    (
        "Why is the feather follicle epithelium specifically significant to how Marek's disease spreads?",
        "It's the one site where MDV replicates and sheds as fully infectious, environmentally stable particles in "
        "skin dander — the actual mechanism behind the disease's wide environmental spread.",
        "It's the site where the virus sheds as fully infectious particles in dander, driving environmental spread",
        "The feather follicle epithelium plays no meaningful role in how the virus actually spreads",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Marek's Disease in Poultry' — sixth of the poultry-only "
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
                organization=org, programme=programme, slug="mareks-disease-in-poultry",
                defaults={
                    "title": "Marek's Disease in Poultry",
                    "subtitle": "A herpesvirus with real tumor-causing potential — and one of the few diseases "
                                 "where vaccination stops the disease but not the infection itself.",
                    "description": "<p>A 4-module continuing-education course on Marek's disease — etiology and "
                                    "the feather-follicle transmission route, the four distinct clinical "
                                    "presentations and their necropsy findings, diagnosis including why "
                                    "histopathology genuinely matters against avian leukosis, and treatment/"
                                    "control/prevention centered on hatch-day vaccination timing.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "A vaccine that stops the tumors but not the virus itself — know the difference",
                    "sales_subheadline": "4 modules on Marek's disease — the four clinical forms, diagnosis "
                                          "against avian leukosis, and why hatch-day vaccination timing is "
                                          "non-negotiable.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners distinguishing Marek's disease from avian leukosis in the field\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Marek's disease CE for vets — clinical forms, diagnosis vs. avian "
                                         "leukosis, and hatch-day vaccination timing.",
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
                organization=org, name="Marek's Disease in Poultry — Final Exam",
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
                title="Final Exam — Marek's Disease in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
