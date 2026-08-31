from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# First of a second, poultry-only ~20-topic batch Sam requested directly
# with vetfresh-6c (on top of the original ~30-topic cross-species
# batch — see seed_newcastle_disease_course.py's header for that
# context). Same single-topic CE micro-course shape and Veterinary CE
# programme. Deliberately goes deeper on ONE disease than the existing
# "Common Viral Diseases"/"Bacterial and Parasitic Disease in Poultry"
# survey modules in the earlier 3-course Poultry series
# (seed_poultry_courses.py) touch on it — same relationship already
# established between Newcastle Disease's own micro-course and that
# series' brief Newcastle coverage, not unplanned duplication.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Why this disease is different from most on this platform</h2>
<p>Chronic respiratory disease (CRD), caused by Mycoplasma gallisepticum (MG), is one of the most economically important poultry diseases worldwide precisely because it rarely kills outright. Instead it quietly depresses egg production, feed conversion, and carcass grade across an entire flock's productive life, often for months before anyone traces the loss back to its real cause.</p>
<h2>What makes MG hard to treat</h2>
<p>Mycoplasma gallisepticum is a small, cell-wall-less bacterium — naturally resistant to every antibiotic class that targets bacterial cell walls, including penicillins and cephalosporins. This single structural fact shapes the entire treatment section of this course. A related organism, Mycoplasma synoviae (MS), causes a similar respiratory picture plus infectious synovitis.</p>
<h2>How it spreads and why it becomes endemic</h2>
<p>Transmission is both vertical (through the egg) and horizontal (contact, airborne, contaminated equipment). MG becomes readily endemic once established — infected birds can carry and intermittently shed for life, and stress reliably triggers flare-ups. Sourcing chicks from MG-free breeder flocks matters just as much here as it does for fowl typhoid and pullorum disease.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>What you'll actually see</h2>
<p>Mild-to-moderate respiratory signs — nasal discharge, tracheal rales, coughing, sneezing, and swollen sinuses, especially in turkeys. Reduced feed intake and a drop in egg production or hatchability is often the first sign a farmer actually notices, well before respiratory signs are obvious. Conjunctivitis appears in some cases.</p>
<h2>Why MG rarely travels alone</h2>
<p>Concurrent infection with E. coli, infectious bronchitis, or Newcastle disease worsens severity dramatically — a mild MG case can turn severe fast once one of these joins in, which is exactly why a thorough workup looks beyond MG alone once it's suspected.</p>
<h2>What necropsy shows</h2>
<p>Airsacculitis — thickened, cloudy, sometimes caseous air sacs — is the hallmark finding, often accompanied by sinusitis. Secondary E. coli infection produces the classic "airsacculitis-pericarditis-perihepatitis" triad, a major cause of carcass condemnation at processing.</p>"""),
    ("Diagnosis",
     """<h2>Building the diagnosis</h2>
<p>History matters here more than in most acute diseases: a gradual decline with mild, persistent respiratory signs after a stress event is a classic MG pattern, distinct from the sudden-onset picture of diseases like Newcastle or infectious bronchitis.</p>
<h2>Testing</h2>
<p>Serology — rapid plate agglutination or ELISA — is the standard tool for flock-level screening. PCR is used for confirmation and, importantly, for distinguishing MG from MS, since the two organisms cause similar pictures but call for different management decisions. Necropsy findings from the previous module round out the diagnostic picture.</p>
<h2>Key differentials</h2>
<p>Infectious coryza, infectious bronchitis, Newcastle disease, and colibacillosis all need to be considered — and, as covered in the previous module, colibacillosis in particular is often co-occurring with MG rather than a true alternative diagnosis.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment — and its real limits</h2>
<p>Because MG has no cell wall, treatment relies on tylosin, tilmicosin, or fluoroquinolones where permitted — none of them target the cell wall that most other antibiotics rely on. These reduce signs and shedding but don't reliably clear the carrier state. Once a flock is endemically infected, "eradicate and restart clean" is the only real fix — ongoing treatment manages symptoms, it doesn't create an MG-free flock.</p>
<h2>Prevention — where the real leverage is</h2>
<p>Sourcing from MG/MS-certified-free flocks is the single highest-leverage step available, the same principle established for fowl typhoid and pullorum disease. Routine breeder screening, live or inactivated vaccines for higher-risk operations, and standard biosecurity round out a real prevention program.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment or your local veterinary authority's current guidance. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does Mycoplasma gallisepticum's lack of a cell wall matter for treatment choice?",
        "Most common antibiotic classes (penicillins, cephalosporins) target the bacterial cell wall — since MG has "
        "none, treatment is limited to drug classes like tylosin, tilmicosin, or fluoroquinolones instead.",
        "It rules out entire antibiotic classes that target the cell wall, narrowing real treatment options",
        "It has no real effect on which antibiotics work against MG",
    ),
    (
        "Why is a drop in egg production or hatchability often the first sign of MG a farmer notices?",
        "It frequently precedes obvious respiratory signs, since MG's core impact is a quiet, gradual production "
        "drain rather than an acute, visibly dramatic illness.",
        "Production effects often show up before respiratory signs become clinically obvious",
        "Respiratory signs always appear well before any production drop occurs",
    ),
    (
        "Why can antimicrobial treatment reduce an MG outbreak's severity without actually solving the underlying problem?",
        "It reduces signs and shedding but doesn't reliably clear the carrier state — once endemic, only "
        "eradicating and restarting clean genuinely removes MG from the flock.",
        "It manages symptoms and shedding without reliably clearing the underlying carrier state",
        "Treatment fully eliminates the carrier state whenever it's applied correctly",
    ),
    (
        "Why does PCR testing matter specifically for distinguishing MG from MS, beyond simple confirmation?",
        "The two organisms cause a similar clinical picture but call for different management decisions, so "
        "correctly telling them apart directly changes what the farm should actually do next.",
        "MG and MS look clinically similar but require different management responses once identified",
        "MG and MS are functionally identical in every respect, so distinguishing them has no practical value",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Mycoplasmosis (Chronic Respiratory Disease) in Poultry' — first of the "
        "second, poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="mycoplasmosis-crd-in-poultry",
                defaults={
                    "title": "Mycoplasmosis (Chronic Respiratory Disease) in Poultry",
                    "subtitle": "The disease that rarely kills outright but quietly drains egg production, feed "
                                 "conversion, and carcass grade for months.",
                    "description": "<p>A 4-module continuing-education course on avian mycoplasmosis (CRD) — "
                                    "etiology and why the lack of a cell wall shapes every treatment decision, "
                                    "clinical findings and the airsacculitis hallmark, diagnosis including "
                                    "distinguishing MG from MS, and treatment/control/prevention centered on "
                                    "clean-source breeding stock.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "The poultry disease costing you money long before it looks like disease",
                    "sales_subheadline": "4 modules on avian mycoplasmosis (CRD) — the cell-wall-less bacterium "
                                          "that treatment manages but rarely eliminates.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners advising on breeder-flock certification and production-loss investigation\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Avian mycoplasmosis (CRD) CE for vets — etiology, diagnosis, and why "
                                         "clean sourcing beats treatment.",
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
                organization=org, name="Mycoplasmosis (CRD) in Poultry — Final Exam",
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
                title="Final Exam — Mycoplasmosis (CRD) in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
