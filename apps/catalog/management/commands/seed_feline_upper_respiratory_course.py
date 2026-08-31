from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Eighth of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Mostly two viruses acting together</h2>
<p>Feline upper respiratory infection is mostly caused by feline herpesvirus-1 (FHV-1, "feline viral rhinotracheitis") and feline calicivirus (FCV) together. Chlamydia felis and Bordetella bronchiseptica are less common additional causes worth keeping in mind, particularly in a case that doesn't respond as expected.</p>
<h2>The lifelong latency that changes everything</h2>
<p>Transmission is highly contagious via direct contact and respiratory secretions. FHV-1 SPECIFICALLY has a lifelong latent infection after apparent recovery — it persists in nerve tissue and reactivates during stress or immunosuppression. This is the single most important fact in this course: a cat that "had it once" can have recurrent episodes throughout its life, triggered by boarding, illness, or a new pet joining the household.</p>
<h2>Why multi-cat households see more, and more persistent, disease</h2>
<p>Multi-cat households and shelters see disproportionately more disease, and more persistent disease, for exactly the reason above — more cats means more stress triggers, more exposure opportunities, and more latently infected individuals who can reactivate and shed at any time.</p>"""),
    ("Clinical Findings",
     """<h2>The typical presentation</h2>
<p>Sneezing, nasal and ocular discharge, conjunctivitis, and oral ulcers — the oral ulcers more classically point toward calicivirus specifically, worth noting when trying to guess which of the two main causes is more likely responsible in a given case.</p>
<h2>A secondary concern that's easy to underweight</h2>
<p>Reduced appetite from diminished smell during congestion is a genuine SECONDARY concern in cats specifically — appetite loss carries a real hepatic lipidosis risk in cats, independent of the respiratory illness itself. This is worth actively managing, not treated as a minor side effect of the primary infection.</p>
<h2>The eye involvement that needs its own treatment</h2>
<p>FHV-1 can cause corneal ulceration through direct eye involvement, which needs its own targeted treatment separate from the general supportive care given for the rest of the respiratory presentation.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>Usually a clinical diagnosis</h2>
<p>Diagnosis is usually presumptive, made from clinical signs given how characteristic the presentation is. PCR is used when specific pathogen identification actually matters — breeding catteries, or recurrent and refractory cases where knowing exactly what's driving the disease changes management. Differentials: other causes of oral ulceration, dental disease with nasal involvement, and a foreign body.</p>
<h2>Treatment, including the eyes</h2>
<p>Supportive care — nutrition, fluids, keeping eyes and nose clean — along with antivirals and antibiotics for secondary infection per veterinary assessment. Ocular involvement needs its own targeted eye treatment, as covered in the previous module.</p>
<h2>Prevention — reducing severity, not guaranteeing full prevention</h2>
<p>Core vaccination reduces both the severity and the likelihood of infection, but it doesn't fully prevent infection or FHV-1's lifelong latency-and-recurrence pattern — similar in spirit to Marek's disease vaccination in poultry, which prevents disease but not infection itself, already covered in its own course on this platform. Reducing stress in multi-cat households helps limit reactivation, directly addressing the mechanism covered in the epidemiology module.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why can a cat that recovered from FHV-1 once develop recurrent respiratory episodes years later?",
        "FHV-1 establishes lifelong latent infection in nerve tissue after apparent recovery, and this latent "
        "virus reactivates during stress or immunosuppression — recurrence isn't a treatment failure.",
        "FHV-1 persists as a lifelong latent infection that reactivates during stress or immunosuppression",
        "Recurrent episodes always indicate the original treatment failed to clear the initial infection",
    ),
    (
        "Why do multi-cat households and shelters see disproportionately more persistent feline respiratory disease?",
        "More cats means more stress triggers and more latently infected individuals who can reactivate and shed "
        "at any time, compounding both exposure opportunities and reactivation risk.",
        "More cats means more stress triggers and more latently infected individuals able to reactivate and shed",
        "Multi-cat households have no particular connection to disease persistence beyond simple exposure numbers",
    ),
    (
        "Why is reduced appetite during a feline respiratory infection treated as a genuine secondary concern, not just a symptom?",
        "It carries a real hepatic lipidosis risk in cats specifically, independent of the respiratory illness "
        "itself — a risk that needs its own active management, not just monitoring.",
        "It carries a real hepatic lipidosis risk in cats, independent of the underlying respiratory illness",
        "Reduced appetite during respiratory illness carries no meaningful additional risk in cats",
    ),
    (
        "In what sense is core FHV-1/FCV vaccination similar to Marek's disease vaccination in poultry?",
        "Both reduce the severity and likelihood of disease without fully preventing infection or, in FHV-1's "
        "case, its lifelong latency and recurrence pattern.",
        "Both reduce disease severity/likelihood without fully preventing infection or (for FHV-1) latency",
        "Both vaccines fully prevent infection outright, with no risk of the pathogen persisting afterward",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Upper Respiratory Infections' — eighth of the mixed dogs/"
        "cats/livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="feline-upper-respiratory-infections",
                defaults={
                    "title": "Feline Upper Respiratory Infections",
                    "subtitle": "A cat that \"had it once\" can have it again — the main viral cause hides in "
                                 "nerve tissue for life and can reactivate any time the cat is stressed.",
                    "description": "<p>A 3-module continuing-education course on feline upper respiratory "
                                    "infections — etiology and FHV-1's lifelong latency that redefines what "
                                    "'recurrence' means, clinical findings including the hepatic lipidosis risk "
                                    "from appetite loss, and diagnosis/treatment/prevention centered on managing "
                                    "recurrence, not just treating a single episode.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Recurrence isn't a treatment failure — it's how this virus actually works",
                    "sales_subheadline": "3 modules on feline upper respiratory infections — FHV-1's lifelong "
                                          "latency, hidden appetite-loss risk, and managing recurrence long-term.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners serving multi-cat households, shelters, or breeding catteries\n"
                        "Anyone counseling owners frustrated by a cat's repeated respiratory episodes"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline URI CE for vets — FHV-1 lifelong latency, hidden appetite-loss "
                                         "risk, and managing recurrence long-term.",
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
                organization=org, name="Feline Upper Respiratory Infections — Final Exam",
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
                title="Final Exam — Feline Upper Respiratory Infections",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
