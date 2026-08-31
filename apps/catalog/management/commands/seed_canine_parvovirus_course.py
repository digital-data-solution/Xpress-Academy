from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourth of the ~30-topic Vet-blog cross-promotion batch (see
# seed_newcastle_disease_course.py's header for full context). Same
# single-topic CE micro-course shape, Veterinary Continuing Education
# programme — VET audience, since the diagnostic/treatment depth here
# (SNAP tests, leukopenia as a prognostic indicator, IV fluid protocols)
# is clinical-practice content, not lay owner-facing guidance.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A remarkably durable virus</h2>
<p>Canine parvovirus (CPV) is a small, non-enveloped, single-stranded DNA virus in the family Parvoviridae. The currently circulating strains worldwide are the CPV-2a, -2b, and -2c variants. Because it's non-enveloped, the virus is remarkably resistant to heat, drying, and most common disinfectants, and can persist in contaminated soil or surfaces for many months to over a year — a fact that shapes essentially every control decision covered later in this course.</p>
<h2>How it spreads</h2>
<p>CPV is shed in extremely high quantities in the feces of infected dogs, beginning before clinical signs appear and continuing for one to two weeks after recovery. Transmission is fecal-oral — direct or indirect via contaminated soil, bedding, food/water bowls, hands, and footwear.</p>
<h2>Who's actually at risk</h2>
<p>Puppies between six weeks and six months are at highest risk, corresponding to the window when maternal antibody has waned but the vaccination series is not yet complete. This is one of the most important facts in this course: the age of highest risk is defined by the vaccination series itself, not by the dog's environment alone.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>The typical presentation</h2>
<p>Sudden onset of lethargy and anorexia, followed rapidly by vomiting and profuse, often hemorrhagic, foul-smelling diarrhea. Fever, or in severe cases hypothermia, marked dehydration developing quickly, and abdominal pain on palpation are all common.</p>
<h2>The rarer cardiac form</h2>
<p>A cardiac form can affect very young puppies infected in utero or shortly after birth, causing sudden death from myocarditis — far less common than the intestinal form, but worth knowing given how differently it presents.</p>
<h2>Why the pathology looks the way it does</h2>
<p>The virus targets rapidly dividing cells — intestinal crypt epithelium, bone marrow, and, in the cardiac form, myocardial cells. Gross necropsy findings include a thickened, hemorrhagic, foul-smelling small intestine and enlarged, edematous mesenteric lymph nodes; histopathology shows crypt necrosis and villous blunting. This same crypt-targeting explains the bloodwork finding covered in the next module.</p>"""),
    ("Diagnosis",
     """<h2>The standard in-clinic test</h2>
<p>Fecal antigen ELISA (the SNAP test) is the standard in-clinic diagnostic — fast and practical, but it can give false negatives very early or very late in infection, so a negative result in a puppy with a classic presentation shouldn't end the workup.</p>
<h2>When more sensitivity is needed</h2>
<p>PCR testing is more sensitive and can distinguish vaccine strain shedding from field-strain infection — useful when SNAP results are ambiguous or when distinguishing a recently vaccinated puppy from a genuine field infection matters clinically.</p>
<h2>Bloodwork as a prognostic tool</h2>
<p>Bloodwork commonly shows marked leukopenia, particularly lymphopenia and neutropenia — a direct consequence of the virus's bone-marrow tropism described in the previous module, and a useful prognostic indicator, not just a diagnostic one.</p>
<h2>Key differentials</h2>
<p>Coronavirus enteritis, salmonellosis, intestinal parasitism, dietary indiscretion or a foreign body, and intussusception all need to be considered before settling on a CPV diagnosis.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment — supportive, but genuinely life-saving</h2>
<p>No drug kills the virus directly. Treatment is intensive supportive care: aggressive IV fluid therapy, anti-emetics, broad-spectrum antibiotics for secondary bacterial sepsis, and early nutritional support. This isn't a minor distinction — with aggressive hospitalization, survival rates are commonly above 80-90%; without treatment, mortality can exceed 90%. The gap between those two numbers is entirely a function of how aggressively supportive care is delivered.</p>
<h2>Control once a case is identified</h2>
<p>Isolate suspected/confirmed cases immediately. Disinfect with a product proven effective against non-enveloped viruses — diluted bleach or accelerated hydrogen peroxide; most everyday disinfectants simply don't work against this virus. Any new puppy should be considered at risk in a household or kennel with a recent case, given how long the virus persists in the environment.</p>
<h2>Prevention — the only reliable answer</h2>
<p>A complete puppy vaccination series (starting around 6-8 weeks, boosted every 3-4 weeks until at least 16 weeks) is the only reliable prevention. Puppies shouldn't be walked in public or exposed to unknown dogs until the series is complete. Breeders and sellers should avoid mixing litters of different ages or sources without knowing their full vaccination and health status.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment or a specific hospitalization protocol for an individual patient. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does canine parvovirus persist in an environment for months even after the infected dog is gone?",
        "It's a non-enveloped virus, which makes it remarkably resistant to heat, drying, and most common "
        "disinfectants — this durability is what drives most of the control recommendations in this course.",
        "It's non-enveloped, making it unusually resistant to heat, drying, and most everyday disinfectants",
        "The virus is airborne and continuously re-deposits itself from the surrounding atmosphere",
    ),
    (
        "Why are puppies between six weeks and six months specifically at highest risk for CPV?",
        "This window is exactly when maternal antibody has waned but the puppy's own vaccination series is not yet "
        "complete — the age of highest risk is defined by the vaccination timeline itself.",
        "It's the window when maternal antibody has faded but the vaccination series isn't finished yet",
        "Puppies outside this age range are naturally immune to parvovirus regardless of vaccination status",
    ),
    (
        "Why shouldn't a negative SNAP (fecal antigen ELISA) test end a CPV workup in a puppy with a classic presentation?",
        "The SNAP test can give false negatives very early or very late in infection, so a negative result doesn't "
        "reliably rule out CPV in a puppy whose clinical picture still strongly suggests it.",
        "It can produce false negatives early or late in the course of infection",
        "The SNAP test is fully reliable at every stage of infection and a negative result is always conclusive",
    ),
    (
        "Why does marked leukopenia (lymphopenia/neutropenia) show up on bloodwork in CPV cases?",
        "The virus targets rapidly dividing cells, including bone marrow, which is the direct cause of the "
        "leukopenia seen on bloodwork — making it a useful prognostic indicator, not just an incidental finding.",
        "The virus's bone-marrow tropism directly causes the leukopenia seen on bloodwork",
        "Leukopenia in CPV cases is unrelated to the virus and reflects a coincidental secondary infection",
    ),
    (
        "Why do everyday disinfectants often fail against CPV-contaminated surfaces?",
        "CPV requires a disinfectant proven effective against non-enveloped viruses specifically — diluted bleach or "
        "accelerated hydrogen peroxide — while most common household disinfectants aren't formulated for that.",
        "CPV needs a disinfectant proven effective against non-enveloped viruses, which most everyday products aren't",
        "Any general-purpose disinfectant is equally effective against CPV as against any other pathogen",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Canine Parvovirus: Recognizing and Responding to a Veterinary Emergency' — "
        "fourth of the ~30-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="canine-parvovirus",
                defaults={
                    "title": "Canine Parvovirus: Recognizing and Responding to a Veterinary Emergency",
                    "subtitle": "Why an environmentally indestructible virus remains one of the leading killers of "
                                 "unvaccinated puppies, and what actually saves them.",
                    "description": "<p>A 4-module continuing-education course on canine parvovirus — etiology and "
                                    "the virus's extraordinary environmental durability, clinical presentation and "
                                    "the pathology behind it, diagnosis including SNAP/PCR testing and leukopenia as "
                                    "a prognostic tool, and treatment/control/prevention centered on aggressive "
                                    "supportive care and complete vaccination series.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "The gap between 90% mortality and 90% survival is entirely how you treat it",
                    "sales_subheadline": "4 modules on canine parvovirus — durability, pathology, diagnosis, and "
                                          "the aggressive supportive care protocol that actually saves puppies.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or emergency practice\n"
                        "Practitioners wanting a focused refresher on one of the most common puppy emergencies\n"
                        "Anyone advising breeders/sellers on vaccination-series timing and litter-mixing risk"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Canine parvovirus CE for vets — pathology, diagnosis, and the supportive "
                                         "care protocol behind real survival rates.",
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
                organization=org, name="Canine Parvovirus — Final Exam",
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
                title="Final Exam — Canine Parvovirus",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
