from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Twelfth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("The Main Worm Types",
     """<h2>Roundworms — the most common</h2>
<p>Ascaridia galli is the most common roundworm in poultry, transmitted by ingestion of eggs or larvae from contaminated litter or soil.</p>
<h2>Cecal worms — a control point for a completely different disease</h2>
<p>Heterakis gallinarum, the cecal worm, matters for a reason that has nothing to do with the worm itself: it carries the protozoan responsible for histomoniasis (blackhead disease). This means cecal worm control IS blackhead prevention — a connection worth understanding on its own, and covered in full in this platform's separate Histomoniasis course.</p>
<h2>Capillary worms and tapeworms</h2>
<p>Capillary worms, affecting the crop, esophagus, and intestine, cause significant blood loss even at relatively low burden. Tapeworms (Raillietina spp.) need an intermediate host — beetles, insects, or snails — to complete their life cycle, which is exactly why they're common in free-range and backyard birds with access to these hosts and rare in fully confined systems.</p>"""),
    ("Epidemiology and Clinical Findings",
     """<h2>Production system drives burden more than almost any other factor</h2>
<p>Transmission is via ingestion of eggs or larvae from contaminated litter/soil, or via an intermediate host for tapeworms. Production system matters directly here: free-range and backyard birds carry substantially higher worm burden than confined litter systems, which break several of these life cycles simply by limiting soil/ground contact.</p>
<h2>What you'll see, and when</h2>
<p>At low burden, infection is often subclinical. Heavier burdens produce poor growth, reduced feed efficiency, pale comb from anemia (especially with capillary worms), diarrhea, reduced egg production, and in severe cases, intestinal blockage or rupture. A "slow flock" with no obvious disease is a real reason to consider worm burden as part of the workup.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>Test, don't guess</h2>
<p>Fecal float testing is the standard, practical, routine diagnostic tool — and the right way to decide deworming frequency, rather than deworming on a fixed schedule without ever confirming whether it's actually needed. Direct observation at necropsy also confirms worm burden where relevant.</p>
<h2>Treatment — a vet decision, not a generic one</h2>
<p>Anthelmintic drug choice, dose, and schedule are best set by a veterinarian, given real concerns around resistance and withdrawal periods for meat and egg-producing birds. Routine, scheduled deworming — not just reactive treatment after signs appear — is standard for any outdoor or litter-access system.</p>
<h2>Reducing burden beyond deworming alone</h2>
<p>Litter management (dry litter reduces egg and larvae survival), range rotation, and separating age groups matter too — older birds typically carry heavier burdens and can seed litter with eggs that then infect younger, more vulnerable birds sharing the same ground.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment on a specific deworming protocol. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does controlling cecal worms (Heterakis gallinarum) matter beyond the worm's own direct damage?",
        "Cecal worms carry the protozoan responsible for histomoniasis (blackhead disease) — controlling the worm "
        "directly interrupts that disease's transmission route as well.",
        "They carry the protozoan responsible for histomoniasis, so worm control also controls that separate disease",
        "Cecal worms have no relevance to any disease beyond the direct intestinal damage they themselves cause",
    ),
    (
        "Why do free-range and backyard birds typically carry a much higher worm burden than confined litter systems?",
        "Confined litter systems break several worm life cycles by limiting the birds' contact with contaminated "
        "soil and ground, while free-range access exposes birds to those same life cycles continuously.",
        "Confined systems limit soil/ground contact, which breaks several of these worms' life cycles directly",
        "Worm burden is identical across production systems and unrelated to how much ground contact birds have",
    ),
    (
        "Why is fecal float testing recommended over deworming on a fixed schedule without testing?",
        "It's the practical way to actually confirm whether deworming is needed and how often, rather than "
        "treating on a guess — testing should guide the schedule, not the other way around.",
        "It confirms actual worm burden, letting deworming frequency be based on evidence rather than a guess",
        "Fixed-schedule deworming without any testing is always more reliable than fecal float testing",
    ),
    (
        "Why can older birds in a mixed-age flock indirectly increase worm risk for younger birds sharing the same ground?",
        "Older birds typically carry heavier worm burdens and can seed the shared litter with eggs, which then "
        "become a source of infection for the younger, more vulnerable birds using the same space.",
        "Older birds carrying heavier burdens can seed shared litter with eggs that then infect younger birds",
        "Worm burden in older birds has no meaningful effect on younger birds sharing the same litter",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Helminthiasis in Poultry: Worms and Deworming' — twelfth of the "
        "poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="helminthiasis-in-poultry",
                defaults={
                    "title": "Helminthiasis in Poultry: Worms and Deworming",
                    "subtitle": "Free-range and backyard birds carry meaningfully more worm burden than confined "
                                 "flocks — and one specific worm matters for a reason beyond itself.",
                    "description": "<p>A 3-module continuing-education course on poultry helminthiasis — the main "
                                    "worm types including the cecal worm/histomoniasis connection, epidemiology "
                                    "and clinical findings by production system, and diagnosis/treatment/"
                                    "prevention centered on fecal float testing over guesswork.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "A 'slow flock' with no obvious disease? Worm burden deserves a real look",
                    "sales_subheadline": "3 modules on poultry helminthiasis — worm types, production-system "
                                          "burden, and testing-guided deworming rather than a fixed schedule.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners investigating unexplained poor growth or feed efficiency\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Poultry helminthiasis CE for vets — worm types, production-system burden, "
                                         "and testing-guided deworming.",
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
                organization=org, name="Helminthiasis in Poultry — Final Exam",
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
                title="Final Exam — Helminthiasis in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
