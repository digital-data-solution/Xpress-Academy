from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Twelfth and final of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context; vetfresh-6c
# says this completes the batch, but Sam may send more later). Same
# no-dedicated-livestock-Programme precedent as FMD and Trypanosomiasis.
# Repeatedly cross-references seed_mycoplasmosis_poultry_course.py —
# same cell-wall-less genus, same treatment limitation, same
# chronic-carrier-shedding pattern, matching how the source article
# itself framed the comparison.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>The same cell-wall trick, in cattle instead of poultry</h2>
<p>Contagious bovine pleuropneumonia (CBPP) is caused by Mycoplasma mycoides subspecies mycoides — cell-wall-less, exactly like the poultry Mycoplasma species already covered in this platform's Mycoplasmosis (CRD) course, and this shared structural fact narrows the effective antibiotic classes in cattle the same way it does in poultry.</p>
<h2>How it spreads, and why it's a real trade disease</h2>
<p>Transmission is via respiratory aerosol from close, prolonged contact — dense grazing, shared water points, and cattle trade or movement, including the long-distance trade routes common in parts of Africa, are the main spread mechanisms. CBPP is a serious economic and trade disease in sub-Saharan Africa, and notifiable.</p>
<h2>The chronic carrier problem — a familiar pattern</h2>
<p>CHRONIC CARRIERS, with walled-off lung sequestra, shed intermittently long after apparent recovery — the same pattern already established for fowl typhoid and poultry mycoplasmosis. These carriers are a recognized source of new outbreaks when moved into a naive herd, which is exactly why the trade-and-movement transmission route covered above is such a persistent risk.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>What you'll see</h2>
<p>Fever, depression, and respiratory signs — labored breathing, coughing, reluctance to move, and a characteristic elbows-abducted, neck-extended posture. Acute cases can progress to rapid death; chronic cases show persistent poor condition with intermittent signs, tying directly to the carrier state covered in the previous module.</p>
<h2>The hallmark, genuinely diagnostic necropsy finding</h2>
<p>Hepatized lung with a distinctive MARBLED appearance on cut section — fibrin deposition and interlobular edema — often accompanied by pleural fluid, is genuinely diagnostic at necropsy. In chronic cases, encapsulated sequestra represent the physical source of the long-term shedding already discussed.</p>"""),
    ("Diagnosis, Treatment, and Control",
     """<h2>Building the diagnosis</h2>
<p>Characteristic clinical and post-mortem findings raise strong suspicion, particularly the marbled lung appearance. Culture is technically demanding; PCR and serology (complement fixation historically the standard, with ELISA increasingly used) confirm and support surveillance. The key differential is other bovine respiratory disease — marbled lung is a strong clue, but lab confirmation still matters given CBPP's regulatory significance.</p>
<h2>Treatment — the same limitation as poultry Mycoplasma</h2>
<p>Antibiotics targeting Mycoplasma reduce severity but DO NOT reliably clear infection or the carrier/sequestra state — the exact same limitation already established for poultry CRD. This isn't a coincidence: it follows directly from the shared cell-wall-less biology covered in the etiology module.</p>
<h2>Control and prevention</h2>
<p>Movement control and quarantine matter given how trade-driven the spread is — various national programs use movement restriction, treatment, and sometimes culling. Vaccination exists, but its efficacy and duration are more limited than many other livestock vaccines, making it one component of control rather than a complete solution on its own. Controlling and documenting movement and trade sourcing is a major, practical lever, arguably as important as any single medical intervention.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's or national veterinary authority's own guidance on a specific outbreak. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does CBPP's cell-wall-less biology matter for treatment, the same way it does for poultry mycoplasmosis?",
        "It narrows the effective antibiotic classes available, since drugs targeting the bacterial cell wall have "
        "nothing to act on — the same structural limitation already established in the poultry disease.",
        "It narrows the effective antibiotic classes, since cell-wall-targeting drugs have nothing to act on",
        "CBPP's cell-wall structure has no real bearing on which antibiotics are effective against it",
    ),
    (
        "Why are chronic CBPP carriers with lung sequestra a recognized source of new outbreaks?",
        "They shed the organism intermittently long after apparent recovery, so moving an apparently recovered "
        "animal into a naive herd can seed a new outbreak despite the animal looking healthy.",
        "They shed intermittently long after apparent recovery, so moving them into a naive herd can seed a new outbreak",
        "Chronic carriers stop shedding the organism entirely once clinical signs have resolved",
    ),
    (
        "Why is the marbled, hepatized lung finding at necropsy considered genuinely diagnostic for CBPP?",
        "It's a distinctive appearance from fibrin deposition and interlobular edema that strongly points toward "
        "CBPP specifically, though lab confirmation still matters given the disease's regulatory significance.",
        "It's a distinctive appearance from fibrin deposition and interlobular edema strongly suggestive of CBPP",
        "The marbled lung finding is a nonspecific sign shared equally across most bovine respiratory diseases",
    ),
    (
        "Why is controlling and documenting cattle movement and trade sourcing described as a major, practical control lever for CBPP?",
        "Respiratory aerosol spread from prolonged contact plus trade-driven movement are the disease's main "
        "spread mechanisms, so controlling movement directly addresses how the disease actually travels.",
        "Trade-driven movement is a main spread mechanism, so controlling it directly addresses how CBPP actually travels",
        "Movement and trade sourcing have little practical bearing on CBPP's actual spread between herds",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Contagious Bovine Pleuropneumonia (CBPP)' — twelfth and final of "
        "the mixed dogs/cats/livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="contagious-bovine-pleuropneumonia",
                defaults={
                    "title": "Contagious Bovine Pleuropneumonia (CBPP)",
                    "subtitle": "A Mycoplasma disease of cattle with the same cell-wall trick that narrows "
                                 "treatment for its poultry cousin — and chronic carriers that can seed a new "
                                 "outbreak long after they seem recovered.",
                    "description": "<p>A 3-module continuing-education course on CBPP — etiology and the shared "
                                    "cell-wall-less biology with poultry mycoplasmosis, clinical findings "
                                    "including the genuinely diagnostic marbled-lung necropsy finding, and "
                                    "diagnosis/treatment/control centered on movement control given trade-driven "
                                    "spread and real treatment limitations.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "The same cell-wall trick as poultry mycoplasmosis — cattle version",
                    "sales_subheadline": "3 modules on CBPP — the marbled-lung necropsy finding, chronic-carrier "
                                          "shedding, and why movement control matters as much as treatment.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving cattle operations\n"
                        "Practitioners advising on herd sourcing and movement/trade compliance\n"
                        "Anyone who's taken the Mycoplasmosis (CRD) course and wants the livestock parallel"
                    ),
                    "not_for": (
                        "Farmers without veterinary training looking for basic livestock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "CBPP CE for vets — marbled-lung diagnosis, chronic-carrier shedding, and "
                                         "movement control given trade-driven spread.",
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
                organization=org, name="Contagious Bovine Pleuropneumonia (CBPP) — Final Exam",
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
                title="Final Exam — Contagious Bovine Pleuropneumonia (CBPP)",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
