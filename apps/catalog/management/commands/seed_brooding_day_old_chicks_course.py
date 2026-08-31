from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Third of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Unlike
# the disease-specific courses in this batch, this one is a practical
# husbandry guide — module breakdown follows the article's own
# temperature/water/feed/space+litter structure rather than the usual
# etiology/clinical/diagnosis/treatment shape.

MODULES = [
    ("Temperature: The Biggest Lever",
     """<h2>Why the first two weeks matter more than any single disease</h2>
<p>A day-old chick cannot regulate its own body temperature effectively and has no functional immune memory yet. Most preventable poultry mortality and lifetime performance loss in Nigeria traces back to brooding fundamentals done slightly wrong in the first two weeks — not to a dramatic disease outbreak.</p>
<h2>Getting the numbers right, then stepping them down</h2>
<p>Target roughly 32-35°C under the brooder for day-olds, stepped down 2-3°C weekly toward ambient by week 4-5. That schedule is a starting point, not a rule — the real signal is the chicks themselves.</p>
<h2>Read the chicks, not just the thermometer</h2>
<p>Evenly spread chicks mean the temperature is correct. Chicks huddled directly under the heat source mean it's too cold. Chicks pushed to the edges and panting mean it's too hot. Draft-free housing matters as much as the heat source itself — a good heat lamp in a drafty house can still leave chicks cold.</p>"""),
    ("Water and Feed",
     """<h2>Water comes first — before feed</h2>
<p>Water should be available within the first one to two hours of arrival, before feed. Early dehydration has outsized, hard-to-recover effects on a chick this young. Water should be cool, clean, and placed near the heat source initially so chicks don't have to travel far from warmth to find it. A vitamin/electrolyte supplement for the first three to five days is common practice to help chicks recover from transport stress.</p>
<h2>Feed — continuous access, careful transitions</h2>
<p>High-quality starter feed should be continuously available, since chicks eat frequently in small amounts rather than in a few large meals. Supplementary trays or paper placed near the main feeders in the first days help chicks actually find the food. Never switch feed type abruptly — transition gradually over several days whenever a change is needed.</p>"""),
    ("Space, Litter, and Hygiene",
     """<h2>Space — plan for the end, not the start</h2>
<p>Overcrowding compounds every other risk on this list: worse temperature control, more disease transmission, and a direct smothering risk. Plan stocking density for the END of the brooding period, not the start — a house that looks comfortably spaced on day one can become dangerously crowded by week three if density was set for day-old chicks alone.</p>
<h2>Litter and the coccidiosis connection</h2>
<p>Dry, absorbent litter at 5-10cm depth keeps chicks warm and reduces ammonia buildup. Damp litter is a double risk: it's both a chilling risk and a coccidiosis risk, since coccidia oocysts thrive specifically in warm, damp litter.</p>
<h2>Why ammonia matters beyond the smell</h2>
<p>Ammonia buildup damages the respiratory tract — the same tissue that diseases like infectious bronchitis and mycoplasmosis go on to exploit. Good litter and ventilation management in the brooding phase is, in a real sense, disease prevention for problems that show up weeks later.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "When assessing brooder temperature, why should chick behavior be trusted over the thermometer reading alone?",
        "Chick behavior (evenly spread vs. huddled vs. pushed to the edges) directly reflects what the chicks are "
        "actually experiencing, which can differ from a single thermometer reading due to drafts or uneven heat "
        "distribution.",
        "It directly shows what chicks are actually experiencing, which a single thermometer reading can miss",
        "Chick behavior and thermometer readings always agree perfectly, so either works equally well",
    ),
    (
        "Why should water be made available before feed in the first hours after chick arrival?",
        "Early dehydration has outsized, hard-to-recover effects on a day-old chick — water access takes priority "
        "over feed access in that critical early window.",
        "Early dehydration has outsized, hard-to-recover effects compared to a short delay in feed access",
        "Feed access matters more than water in the first hours, so water can reasonably wait",
    ),
    (
        "Why should stocking density be planned for the end of the brooding period rather than the start?",
        "A house that looks comfortably spaced for day-old chicks can become dangerously overcrowded by several "
        "weeks in if density was only set for the smaller starting birds.",
        "Chicks grow substantially during brooding, so day-one spacing can become overcrowded by the period's end",
        "Stocking density has no meaningful effect on outcomes regardless of when it's planned for",
    ),
    (
        "Why is damp litter considered a double risk rather than just a chilling concern?",
        "Damp litter is both a chilling risk and a coccidiosis risk, since coccidia oocysts specifically thrive in "
        "warm, damp litter conditions.",
        "It's both a chilling risk and a coccidiosis risk, since oocysts thrive in warm, damp conditions",
        "Damp litter only affects chick comfort and has no connection to any specific disease risk",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Brooding Day-Old Chicks: Getting the First Two Weeks Right' — third of "
        "the poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="brooding-day-old-chicks",
                defaults={
                    "title": "Brooding Day-Old Chicks: Getting the First Two Weeks Right",
                    "subtitle": "Most preventable poultry mortality traces back to brooding fundamentals, not a "
                                 "dramatic disease outbreak.",
                    "description": "<p>A 3-module continuing-education course on brooding day-old chicks — "
                                    "temperature management and reading chick behavior, water and feed access in "
                                    "the critical first hours, and space/litter/hygiene practices that prevent "
                                    "problems weeks before they'd otherwise appear.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "The first two weeks decide more than any single disease you'll diagnose later",
                    "sales_subheadline": "3 modules on brooding fundamentals — temperature, water/feed timing, and "
                                          "the litter practices that prevent disease weeks before it appears.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs advising poultry operations on management practices\n"
                        "Practitioners investigating unexplained early mortality or poor lifetime performance\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training — though the content is practical enough "
                        "to be useful with veterinary guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Chick brooding CE for vets — temperature, water/feed timing, and litter "
                                         "practices that prevent later disease.",
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
                organization=org, name="Brooding Day-Old Chicks — Final Exam",
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
                title="Final Exam — Brooding Day-Old Chicks",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
