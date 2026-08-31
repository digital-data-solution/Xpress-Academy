from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Second of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("Etiology and an Indoor-Adapted Vector",
     """<h2>What causes it, and how it actually gets in</h2>
<p>Ehrlichiosis in dogs is most significantly caused by Ehrlichia canis, an intracellular bacterium transmitted by the brown dog tick (Rhipicephalus sanguineus). What makes this tick genuinely different from most others is its indoor adaptation: it's uniquely capable of living and completing its entire life cycle INDOORS, in homes and kennels, unlike most ticks that require outdoor vegetation. The brown dog tick lives indoors as happily as outdoors — this isn't purely an outdoor-dog risk.</p>
<h2>Where it's found, and how transmission happens</h2>
<p>Ehrlichiosis is endemic wherever the brown dog tick is established, which includes much of Nigeria given the tick's climate adaptability. Transmission requires real tick attachment and feeding time, not instant contact on exposure.</p>"""),
    ("Clinical Findings — Three Phases",
     """<h2>Acute phase</h2>
<p>Roughly two to four weeks post-infection: fever, lethargy, enlarged lymph nodes, and sometimes nosebleeds.</p>
<h2>Subclinical phase — genuinely deceptive</h2>
<p>The dog appears NORMAL while the organism persists for months to years. This phase is genuinely deceptive — a dog can carry the infection silently for months, looking entirely healthy while the disease progresses unseen toward the chronic phase below.</p>
<h2>Chronic phase</h2>
<p>Months to years later: severe bone marrow suppression, bleeding tendencies, weight loss, and eye inflammation, which can be fatal. By this point, the damage from prolonged subclinical infection has already accumulated, which is why catching the disease earlier matters so much.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>A strong early clue</h2>
<p>Bloodwork often shows low platelets (thrombocytopenia) — a strong clue in an endemic area, worth actively considering even before other signs point clearly toward ehrlichiosis. PCR confirms current infection. Antibody testing can reflect past exposure rather than necessarily active infection, so it needs to be interpreted with that limitation in mind. Key differentials: babesiosis, anaplasmosis, and other causes of thrombocytopenia.</p>
<h2>Treatment — better caught early</h2>
<p>Doxycycline, given over a multi-week course, is the standard treatment. Response is good if caught in the acute phase, but less predictable in the chronic phase once real bone marrow damage has already occurred — another reason the subclinical phase's deceptiveness matters so much clinically.</p>
<h2>Why treating the dog alone often fails</h2>
<p>Control needs BOTH the dog and the environment treated — the tick lives in the environment too, the same principle already established for poultry red mite in its own course. Treating the dog alone in an infested home or kennel often fails, since the tick population in the environment simply reinfests. Routine tick preventives, regular checks, and environmental tick control together form real prevention.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is the brown dog tick a risk even for dogs that never go outdoors?",
        "It's uniquely adapted to living and completing its entire life cycle indoors, in homes and kennels, "
        "unlike most ticks that require outdoor vegetation.",
        "It's uniquely capable of living and completing its life cycle entirely indoors, unlike most other ticks",
        "The brown dog tick cannot survive or reproduce indoors under any circumstances",
    ),
    (
        "Why is ehrlichiosis's subclinical phase considered genuinely deceptive?",
        "The dog appears completely NORMAL while the organism persists for months to years, meaning an infected, "
        "healthy-looking dog can go unnoticed well before chronic-phase damage appears.",
        "A dog can appear completely healthy for months to years while the organism persists and the disease progresses",
        "The subclinical phase causes obvious clinical signs that make infected dogs easy to identify",
    ),
    (
        "Why does low platelet count (thrombocytopenia) on routine bloodwork matter specifically in an endemic area?",
        "It's a strong clue toward ehrlichiosis in that context, worth actively considering even before other more "
        "specific signs point toward the diagnosis.",
        "It's a strong clue toward ehrlichiosis specifically in an area where the brown dog tick is established",
        "Thrombocytopenia has no particular association with ehrlichiosis regardless of geographic area",
    ),
    (
        "Why does treating an infected dog alone often fail to resolve ehrlichiosis in an infested home or kennel?",
        "The tick lives in the environment as well as on the dog, so an infested environment can simply reinfest a "
        "treated dog unless the environment itself is treated too.",
        "The tick lives in the environment too, so an untreated environment can reinfest a dog that's already been treated",
        "Treating the dog alone is always fully sufficient to resolve an ehrlichiosis infestation permanently",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Ehrlichiosis and Tick-Borne Disease in Dogs' — second of the mixed "
        "dogs/cats/livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="ehrlichiosis-tick-borne-disease-dogs",
                defaults={
                    "title": "Ehrlichiosis and Tick-Borne Disease in Dogs",
                    "subtitle": "The brown dog tick lives indoors as happily as outdoors — this isn't purely an "
                                 "outdoor-dog risk, and a dog can carry the infection silently for months.",
                    "description": "<p>A 3-module continuing-education course on canine ehrlichiosis — etiology "
                                    "and the uniquely indoor-adapted brown dog tick vector, the three clinical "
                                    "phases including the deceptive subclinical stage, and diagnosis/treatment/"
                                    "prevention centered on treating both dog and environment together.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "A dog can carry this silently for months while looking completely healthy",
                    "sales_subheadline": "3 modules on canine ehrlichiosis — the indoor-adapted vector, the "
                                          "deceptive subclinical phase, and treating both dog and environment.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or emergency practice\n"
                        "Practitioners investigating unexplained thrombocytopenia in an endemic area\n"
                        "Anyone who's taken the External Parasites course and wants a similar environment-vector pattern"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Canine ehrlichiosis CE for vets — indoor tick vector, deceptive "
                                         "subclinical phase, and dog-plus-environment treatment.",
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
                organization=org, name="Ehrlichiosis and Tick-Borne Disease in Dogs — Final Exam",
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
                title="Final Exam — Ehrlichiosis and Tick-Borne Disease in Dogs",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
