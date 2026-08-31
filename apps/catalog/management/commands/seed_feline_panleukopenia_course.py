from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Seventh of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context). Written to
# explicitly parallel seed_canine_parvovirus_course.py throughout,
# matching how the source article itself framed the comparison.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>The feline counterpart to canine parvovirus</h2>
<p>Feline panleukopenia is caused by feline panleukopenia virus (FPV), a parvovirus closely related to canine parvovirus — already covered in its own course on this platform. Like its canine relative, FPV is non-enveloped and environmentally extremely hardy, persisting for over a year, and shares that virus's same real-world durability challenge for cleaning and control.</p>
<h2>Extremely contagious, and a real reproductive threat</h2>
<p>Transmission is fecal-oral plus contact with a contaminated environment, and spread is extremely contagious. FPV also CROSSES THE PLACENTA — infection of a pregnant queen can cause cerebellar hypoplasia in surviving kittens, a permanent coordination deficit that's genuinely distinct from the systemic disease seen in older kittens and adults, covered in the next module.</p>
<h2>The same vulnerable window as canine parvovirus</h2>
<p>Kittens between weaning and a completed vaccination series are at highest risk for systemic disease — the same window pattern already established for canine parvovirus in dogs, a useful mental model to carry between the two species.</p>"""),
    ("Clinical Findings",
     """<h2>Systemic disease in older kittens and adults</h2>
<p>Sudden lethargy, appetite loss, vomiting, and severe, often bloody diarrhea, with rapid dehydration — a presentation that will look familiar from canine parvovirus, given how closely related the two viruses are.</p>
<h2>The hallmark bloodwork finding</h2>
<p>A dramatic white blood cell drop — panleukopenia, the disease's own namesake — aids diagnosis and explains the severe susceptibility to secondary infection that makes this disease so dangerous.</p>
<h2>The unique in-utero consequence</h2>
<p>Kittens infected very young, or in utero, who survive may show permanent ataxia from cerebellar hypoplasia, without any other ongoing systemic illness — a lasting, visible reminder of an infection that happened before or shortly after birth, distinct from the acute systemic disease covered above.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>Diagnosis — the same SNAP-style approach as canine parvovirus</h2>
<p>Fecal antigen ELISA, the same SNAP-style test used for canine parvovirus given the two viruses' close relation, is the standard diagnostic. Marked leukopenia on bloodwork supports the diagnosis and correlates with severity. Key differentials: FeLV/FIV-related illness, other severe GI causes, and — for a kitten with ataxia — other causes of that specific sign.</p>
<h2>Treatment — the same intensive supportive approach that works</h2>
<p>There is no antiviral treatment. Intensive supportive care — IV fluids, anti-emetics, nutrition, antibiotics for secondary infection — saves lives, the same approach already established for canine parvovirus. Good prognosis follows prompt, aggressive treatment.</p>
<h2>Control and prevention</h2>
<p>Isolation and disinfection with products effective against non-enveloped viruses — bleach, accelerated hydrogen peroxide — are needed, the same durability challenge as canine parvovirus. Prevention is a complete kitten vaccination series through roughly 16 weeks, not just a first shot — completing the full series matters just as much here as it does for the canine equivalent.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does feline panleukopenia share so many practical similarities with canine parvovirus?",
        "FPV is a parvovirus closely related to canine parvovirus, sharing similar environmental hardiness, "
        "transmission, and clinical presentation, which is why the diagnostic and treatment approach parallels it.",
        "FPV is a parvovirus closely related to canine parvovirus, sharing much of its biology and clinical behavior",
        "The two viruses are unrelated and only coincidentally share a similar clinical presentation",
    ),
    (
        "What makes FPV's ability to cross the placenta a uniquely significant fact about this disease?",
        "It can cause cerebellar hypoplasia in surviving kittens — a permanent coordination deficit distinct from "
        "the acute systemic disease seen in older kittens and adults infected after birth.",
        "It can cause permanent cerebellar hypoplasia in kittens infected before or very shortly after birth",
        "Placental crossing has no clinical significance beyond the standard systemic disease seen in older kittens",
    ),
    (
        "Why does the dramatic white blood cell drop (panleukopenia) matter beyond just aiding diagnosis?",
        "It directly explains the severe susceptibility to secondary infection that makes this disease so "
        "dangerous — the finding isn't just diagnostic, it reflects the actual mechanism putting the kitten at risk.",
        "It explains the severe susceptibility to secondary infection that makes the disease so dangerous",
        "The white blood cell count has no real connection to the kitten's risk of secondary infection",
    ),
    (
        "Why does completing the full kitten vaccination series through roughly 16 weeks matter, rather than just the first shot?",
        "A single shot alone doesn't reliably protect through the full vulnerable window between waning maternal "
        "antibody and completed immunity — the same principle already established for canine parvovirus.",
        "A single shot alone doesn't reliably protect through the full vulnerable window before completed immunity",
        "The first shot alone provides essentially complete protection, making the rest of the series largely optional",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Panleukopenia' — seventh of the mixed dogs/cats/livestock "
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
                organization=org, programme=programme, slug="feline-panleukopenia",
                defaults={
                    "title": "Feline Panleukopenia",
                    "subtitle": "The feline counterpart to canine parvovirus — closely related, similarly "
                                 "durable in the environment, and uniquely able to cause permanent brain damage "
                                 "in kittens infected before birth.",
                    "description": "<p>A 3-module continuing-education course on feline panleukopenia — etiology "
                                    "and its close relation to canine parvovirus including the unique placental "
                                    "transmission risk, clinical findings including the hallmark leukopenia and "
                                    "in-utero cerebellar hypoplasia, and diagnosis/treatment/prevention paralleling "
                                    "canine parvovirus's proven approach.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "The feline cousin of parvovirus, with one consequence that's uniquely its own",
                    "sales_subheadline": "3 modules on feline panleukopenia — placental transmission risk, "
                                          "hallmark leukopenia, and treatment paralleling canine parvovirus's approach.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or emergency practice\n"
                        "Practitioners who've taken the Canine Parvovirus course and want the feline parallel\n"
                        "Anyone counseling breeders on kitten vaccination timing"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline panleukopenia CE for vets — placental transmission, hallmark "
                                         "leukopenia, and treatment paralleling canine parvovirus.",
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
                organization=org, name="Feline Panleukopenia — Final Exam",
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
                title="Final Exam — Feline Panleukopenia",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
