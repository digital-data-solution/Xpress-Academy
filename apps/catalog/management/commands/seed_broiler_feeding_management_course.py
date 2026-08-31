from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifteenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Feed Formulation Across the Broiler Cycle",
     """<h2>A compressed timeline where early setbacks matter disproportionately</h2>
<p>A modern broiler reaches market weight in five to seven weeks — a genuinely compressed production cycle where a setback in week one has proportionally bigger lifetime impact than almost any other livestock production system.</p>
<h2>The three phases</h2>
<p>Starter feed (days 0-10) carries the highest nutrient density, given as crumble or mash. Grower feed (days 10-24) transitions to pellet form — and that pellet transition improves feed efficiency on its own, independent of the ration's nutrient content, since birds waste less and eat faster from pellets than from mash. Finisher feed (day 24 to market) carries lower medication and additive levels, respecting the withdrawal periods needed before slaughter.</p>"""),
    ("FCR as an Early-Warning Signal, and Water",
     """<h2>The number that tells you whether things are actually working</h2>
<p>Feed conversion ratio (FCR) is the single number that best captures whether feeding and health management are working together. A RISING FCR with no obvious cause is often the EARLIEST signal of a subclinical health problem — coccidiosis, mycoplasmosis, or worm burden — showing up well before mortality or any visible clinical sign does. FCR deserves to be tracked as seriously as mortality, not treated as a purely economic afterthought.</p>
<h2>Water — an outsized, fast effect given the growth rate</h2>
<p>A broiler's fast growth means water restriction has an outsized, fast effect on performance. Line height, flow, and cleanliness are worth checking routinely rather than assumed to be fine — a problem here can show up in production numbers faster than in most other livestock systems, precisely because of how quickly broilers grow.</p>"""),
    ("Stocking, Ventilation, and Growth-Linked Problems",
     """<h2>Plan for the end-of-cycle weight, not the start</h2>
<p>Rapid growth concentrates weight, heat, moisture, and ammonia into a short timeframe. Stocking density and ventilation should be planned for the END-of-cycle weight, not the start — the same principle already established for brooding day-old chicks, applied here across the full cycle rather than just the first two weeks.</p>
<h2>When growth outpaces the cardiovascular system</h2>
<p>Ascites and sudden death syndrome — each covered in their own dedicated courses on this platform — are consequences of growth outpacing cardiovascular capacity. Feeding and lighting programs that moderate the earliest growth rate slightly are a recognized strategy to reduce both, a real tradeoff against maximum growth speed that's worth discussing directly with a vet or nutritionist rather than defaulting to fastest-possible growth.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's or nutritionist's own formulation and management decisions for a specific operation. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does a setback in a broiler's first week have proportionally bigger lifetime impact than in most other livestock systems?",
        "A modern broiler reaches market weight in just five to seven weeks — a genuinely compressed timeline where "
        "an early problem has less time to be corrected before the production cycle ends.",
        "The production cycle is compressed to five to seven weeks, leaving little time to correct an early setback",
        "Broiler production timelines are actually longer than most livestock systems, reducing early-setback impact",
    ),
    (
        "Why does the pellet transition in grower feed improve feed efficiency on its own?",
        "Birds waste less and eat faster from pellets than from mash, independent of the ration's actual nutrient "
        "content — the physical form of the feed itself is a real efficiency lever.",
        "Birds waste less and eat faster from pellets than mash, independent of the feed's underlying nutrient content",
        "Pellet form has no real effect on feed efficiency compared to mash of the same nutrient content",
    ),
    (
        "Why is a rising FCR with no obvious cause considered a useful early-warning signal?",
        "It's often the earliest sign of a subclinical health problem like coccidiosis, mycoplasmosis, or worm "
        "burden — appearing before mortality or any visible clinical sign does.",
        "It's often the earliest detectable sign of a subclinical health problem, appearing before visible symptoms do",
        "FCR is a purely economic metric with no real connection to underlying flock health",
    ),
    (
        "Why should stocking density and ventilation be planned for a broiler's end-of-cycle weight rather than its starting weight?",
        "Rapid growth concentrates weight, heat, moisture, and ammonia into a short timeframe, so a density set "
        "for day-old birds becomes dangerously inadequate by the time they reach market weight.",
        "Rapid growth means density set for day-old birds becomes inadequate by the time birds reach market weight",
        "Stocking density has no meaningful relationship to a broiler's weight at any point in the cycle",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feeding and Management of Broilers' — fifteenth of the poultry-only "
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
                organization=org, programme=programme, slug="broiler-feeding-and-management",
                defaults={
                    "title": "Feeding and Management of Broilers",
                    "subtitle": "A modern broiler reaches market weight in 5-7 weeks — a setback in week one has "
                                 "proportionally bigger lifetime impact than almost any other livestock.",
                    "description": "<p>A 3-module continuing-education course on broiler feeding and management — "
                                    "feed formulation across the three-phase cycle, FCR as an early-warning "
                                    "health signal and water's outsized impact, and stocking/ventilation planning "
                                    "plus the real link to ascites and sudden death syndrome.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "A rising FCR is often the earliest warning you'll get — before any visible sign",
                    "sales_subheadline": "3 modules on broiler feeding and management — the three-phase cycle, "
                                          "FCR as an early-warning tool, and end-of-cycle stocking planning.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs advising broiler operations\n"
                        "Practitioners investigating a rising FCR with no obvious visible cause\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Broiler feeding CE for vets — three-phase formulation, FCR as an early "
                                         "warning signal, and end-of-cycle stocking planning.",
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
                organization=org, name="Feeding and Management of Broilers — Final Exam",
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
                title="Final Exam — Feeding and Management of Broilers",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
