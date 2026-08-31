from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Third of the ~30-topic Vet-blog cross-promotion batch (see
# seed_newcastle_disease_course.py's header for full context). Same
# single-topic CE micro-course shape, same Veterinary Continuing
# Education programme as the poultry-disease courses before it.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Two related but distinct diseases</h2>
<p>Fowl typhoid and pullorum disease are caused by two closely related, host-adapted Salmonella serovars: <strong>Salmonella Gallinarum</strong> (fowl typhoid) and <strong>Salmonella Pullorum</strong> (pullorum disease). Both are non-motile, host-restricted Gram-negative bacilli, genetically close enough that older literature sometimes groups them together as "S. Gallinarum-Pullorum." Unlike most Salmonella serovars, neither is a significant cause of human foodborne illness, though S. Gallinarum can occasionally cause disease in immunocompromised people.</p>
<h2>How they spread</h2>
<p>Both organisms transmit vertically (transovarian — from an infected hen through the egg) and horizontally via the fecal-oral route, contaminated feed, water, equipment, and carrier birds. This is the key fact that shapes control strategy: a single infected breeder hen can seed an entire day-old chick batch through the hatchery.</p>
<h2>Different age patterns, same underlying threat</h2>
<p>Pullorum disease classically causes high mortality in chicks in the first two to three weeks of life; fowl typhoid tends to affect growing and adult birds, though it can occur at any age. Survivors of both diseases frequently become asymptomatic carriers, shedding intermittently for life — this, not the acute outbreak itself, is the single biggest reason these diseases persist in a flock or region despite apparent recovery.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>In chicks — pullorum disease</h2>
<p>Huddling, drowsiness, weakness, pasty white diarrhea staining vent feathers ("pasted vents"), gasping, and high mortality. Survivors are often stunted.</p>
<h2>In growers and adults — fowl typhoid</h2>
<p>Depression, anorexia, pale and swollen comb/wattles, greenish-yellow diarrhea, and sudden death. In layers, a sharp drop in egg production is often the first thing a farmer notices.</p>
<h2>What necropsy shows</h2>
<p>Enlarged, friable, often bronze- or greenish-discolored liver and spleen are the hallmark findings in fowl typhoid — pinpoint white necrotic foci may also appear on the liver, heart, and gizzard muscle. In pullorum-affected chicks, look for unabsorbed and often caseous yolk sac material, and small grey nodules in the lungs, heart, and gizzard.</p>"""),
    ("Diagnosis",
     """<h2>Building the case</h2>
<p>Flock history and clinical signs consistent with the age pattern (young chicks vs. growers/adults) are the starting point, supported by necropsy findings — particularly the liver and spleen changes described in the previous module.</p>
<h2>Confirmatory testing</h2>
<p>Bacterial culture and isolation from liver, spleen, heart, or yolk sac remains the gold standard. The rapid whole-blood or serum plate agglutination test is widely used for flock-level screening and breeder-flock certification — fast and practical, but it can cross-react with other Salmonella serovars, so a positive flock still needs confirmatory culture.</p>
<h2>Key differentials</h2>
<p>Colibacillosis, other systemic salmonelloses, and omphalitis (yolk sac infection of other bacterial origin) all need to be ruled out before settling on a fowl typhoid or pullorum diagnosis.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment — and its real limit</h2>
<p>Antimicrobial therapy, ideally guided by culture and sensitivity, can reduce mortality during an active outbreak. But it does not reliably eliminate the carrier state — a treated survivor should still be considered a biosecurity risk to the rest of the flock and to future breeding stock, not a cleared bird.</p>
<h2>Control during an outbreak</h2>
<p>Cull confirmed carrier/reactor birds identified on serological screening rather than treating and retaining them, particularly in breeder flocks. Thoroughly clean and disinfect housing and equipment between flocks. Source day-old chicks only from a certified Salmonella-Gallinarum/Pullorum-free breeder flock.</p>
<h2>Prevention — where control programs actually work</h2>
<p>Routine serological screening of breeder flocks, with removal of reactors, is the backbone of pullorum-typhoid control programs worldwide. Combine this with strict all-in/all-out management, rodent control, and careful egg hygiene plus proper incubator/hatchery sanitation — because transovarian transmission means a hatchery can seed an entire day-old chick batch from a single infected breeder hen.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment or your local veterinary authority's current guidance. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why do fowl typhoid and pullorum disease persist in a flock or region even after an outbreak appears to resolve?",
        "Survivors of both diseases frequently become asymptomatic carriers, shedding the organism intermittently for "
        "life — this carrier state, not the acute outbreak itself, is the main reason these diseases persist.",
        "Survivors commonly become lifelong intermittent shedders, which keeps the organism circulating",
        "The bacteria are airborne and re-infect flocks from the surrounding environment indefinitely",
    ),
    (
        "How does the age pattern of pullorum disease differ from fowl typhoid?",
        "Pullorum disease classically strikes chicks in their first two to three weeks of life, while fowl typhoid "
        "tends to affect growing and adult birds, though it can occur at any age.",
        "Pullorum classically strikes very young chicks; fowl typhoid classically strikes growers and adults",
        "Both diseases affect only day-old chicks and never appear in growers or adult birds",
    ),
    (
        "Why is the whole-blood/serum plate agglutination test alone not sufficient to confirm fowl typhoid or pullorum in a flock?",
        "It's fast and practical for flock-level screening, but it can cross-react with other Salmonella serovars, so "
        "a positive result on this test still needs confirmatory bacterial culture.",
        "It can cross-react with other Salmonella serovars, so positive flocks still need confirmatory culture",
        "The plate agglutination test is fully specific and never requires any follow-up confirmation",
    ),
    (
        "Why does antimicrobial treatment during an outbreak not solve the underlying biosecurity problem?",
        "Treatment can reduce mortality in an active outbreak but doesn't reliably clear the carrier state — treated "
        "survivors should still be treated as a biosecurity risk, not a cleared bird.",
        "Treated survivors can still remain carriers and pose an ongoing biosecurity risk to the flock",
        "Antimicrobial treatment fully clears the organism and eliminates any future carrier risk",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Fowl Typhoid and Pullorum Disease: The Salmonella Threat in Nigerian Poultry' — "
        "third of the ~30-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="fowl-typhoid-and-pullorum-disease",
                defaults={
                    "title": "Fowl Typhoid and Pullorum Disease: The Salmonella Threat in Nigerian Poultry",
                    "subtitle": "Two host-adapted Salmonella serovars, the carrier state that keeps them circulating, "
                                 "and the screening programs that actually control them.",
                    "description": "<p>A 4-module continuing-education course on fowl typhoid and pullorum disease — "
                                    "etiology and vertical/horizontal transmission, clinical findings and necropsy "
                                    "lesions by age group, diagnosis including the plate agglutination test's real "
                                    "limits, and treatment/control/prevention centered on breeder-flock screening.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "The Salmonella threat that persists long after the outbreak looks over",
                    "sales_subheadline": "4 modules on fowl typhoid and pullorum disease — the carrier state, "
                                          "necropsy findings, and the screening programs that actually work.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners advising breeder-flock operations on Salmonella screening programs\n"
                        "Anyone working the existing Poultry Health & Biosecurity course who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance — "
                        "see the Poultry Health & Biosecurity course instead"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Fowl typhoid and pullorum disease CE for vets — etiology, diagnosis, and "
                                         "breeder-flock screening programs.",
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
                organization=org, name="Fowl Typhoid and Pullorum Disease — Final Exam",
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
                title="Final Exam — Fowl Typhoid and Pullorum Disease",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
