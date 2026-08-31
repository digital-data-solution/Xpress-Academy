from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Tenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Two damaging effects from one small virus</h2>
<p>Chicken anemia virus (CIAV) is a small, non-enveloped DNA virus that targets bone marrow (erythroid precursors) AND the thymus (T-cell precursors) — which is exactly why it causes anemia and immunosuppression together, not one or the other. Understanding this dual target is the key to understanding everything else in this course.</p>
<h2>Who's actually vulnerable, and for how long</h2>
<p>Transmission is both vertical (through the egg) and horizontal (contact, fecal-oral). The disease is most severe in chicks under roughly three weeks of age that lack maternal antibody protection. Older birds that become infected are typically subclinical for anemia itself, but remain immunosuppressed — more susceptible to secondary infections and showing poor vaccine response even with no overt signs of illness. This subclinical immunosuppression, not the visible anemia, is often the more practically important consequence.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>What overt disease looks like</h2>
<p>Anemia presents as a pale comb, wattles, and skin, along with lethargy, poor growth, and mortality in susceptible young chicks. Subcutaneous and intramuscular hemorrhages can appear, especially with a secondary infection — sometimes called "blue wing disease" in that combined presentation.</p>
<h2>The lesion that matters more than the anemia itself</h2>
<p>Thymus and bursa atrophy drives the immunosuppression covered in the previous module — and in practical terms, this atrophy often matters more than the anemia itself, since it's what leaves a bird vulnerable to everything else circulating on the farm. At necropsy, bone marrow appears pale and watery rather than the normal red, active tissue, alongside the thymic/bursal atrophy and any hemorrhages present.</p>"""),
    ("Diagnosis",
     """<h2>Confirming the virus</h2>
<p>PCR is the standard confirmatory test. Serology is used for breeder-flock screening, tracking whether a breeder population has developed the immunity that protects its chicks through maternal antibody.</p>
<h2>A differential genuinely worth distinguishing</h2>
<p>Aflatoxicosis is a key differential — it also causes both immunosuppression and hemorrhage, making it genuinely worth distinguishing from CIAV rather than assuming one or the other from a similar-looking presentation. Other causes of anemia should also be considered.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Suspect this when vaccination programs "aren't working"</h2>
<p>There is no specific treatment — supportive care and managing secondary infections is the practical response to an active case. But the more useful clinical instinct is knowing when to suspect CIAV in the first place: when a flock's vaccination program seems ineffective, or secondary infections keep recurring without an obvious explanation, immunosuppression from CIAV is worth actively considering.</p>
<h2>The real control point is the breeder flock, not the chick</h2>
<p>Breeder-flock immunity — whether natural or vaccinated — protects chicks through maternal antibody across the vulnerable early window. This is why prevention here targets the breeder pullet BEFORE lay, not the chick directly, the same logic already seen in avian encephalomyelitis-style breeder-timing strategies elsewhere in this course series. General biosecurity rounds out prevention.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does chicken anemia virus cause both anemia and immunosuppression together, rather than just one?",
        "It targets bone marrow (erythroid precursors), producing anemia, AND the thymus (T-cell precursors), "
        "producing immunosuppression — the dual target is the direct cause of both effects appearing together.",
        "It targets both bone marrow and the thymus at once, directly producing both effects together",
        "The immunosuppression is a secondary consequence of the anemia itself, not a separate direct effect",
    ),
    (
        "Why might CIAV's immunosuppression matter more in practice than the anemia it causes?",
        "Older infected birds are often subclinical for anemia but remain immunosuppressed — more susceptible to "
        "secondary infections and poor vaccine response, even with no visible signs of illness.",
        "Subclinical immunosuppression can persist and cause real problems even without any visible anemia",
        "Immunosuppression from CIAV is rare and typically resolves faster than any anemia it causes",
    ),
    (
        "Why is aflatoxicosis specifically worth distinguishing from chicken anemia virus infection?",
        "Both conditions cause immunosuppression and hemorrhage, producing a genuinely similar clinical picture "
        "that a workup needs to actively differentiate rather than assume.",
        "Both conditions cause immunosuppression and hemorrhage, producing a genuinely similar clinical picture",
        "Aflatoxicosis and CIAV have entirely distinct presentations that are never mistaken for one another",
    ),
    (
        "Why does CIAV prevention focus on vaccinating breeder pullets before lay, rather than vaccinating chicks directly?",
        "Breeder-flock immunity protects chicks through maternal antibody across their vulnerable early window — "
        "the real control point is upstream of the chick, not the chick's own vaccination.",
        "Maternal antibody from an immune breeder flock protects chicks through their most vulnerable early weeks",
        "Chick-level vaccination is equally effective and breeder timing makes no real practical difference",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Chicken Anemia Virus Infection' — tenth of the poultry-only "
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
                organization=org, programme=programme, slug="chicken-anemia-virus-infection",
                defaults={
                    "title": "Chicken Anemia Virus Infection",
                    "subtitle": "A virus doing two damaging things at once — causing anemia directly, and quietly "
                                 "undermining every other vaccine and disease-control effort.",
                    "description": "<p>A 4-module continuing-education course on chicken anemia virus — etiology "
                                    "and the dual bone-marrow/thymus target that causes anemia and "
                                    "immunosuppression together, clinical findings, diagnosis including the "
                                    "aflatoxicosis differential, and treatment/control/prevention centered on "
                                    "breeder-pullet vaccination before lay.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Suspect this when a vaccination program 'just isn't working'",
                    "sales_subheadline": "4 modules on chicken anemia virus — the anemia/immunosuppression combo, "
                                          "diagnosis, and why breeder-pullet timing is the real prevention lever.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners troubleshooting recurring secondary infections or poor vaccine response\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Chicken anemia virus CE for vets — anemia plus immunosuppression, "
                                         "diagnosis, and breeder-pullet vaccination timing.",
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
                organization=org, name="Chicken Anemia Virus Infection — Final Exam",
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
                title="Final Exam — Chicken Anemia Virus Infection",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
