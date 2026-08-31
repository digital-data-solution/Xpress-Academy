from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Sixteenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("The Normal Production Curve",
     """<h2>Knowing normal is what lets you spot a real problem</h2>
<p>Lay begins around 18-20 weeks of age, peaks — often above 90% hen-day production — within a few weeks, then gradually declines over the rest of the production cycle. Understanding this curve is genuinely the foundation of good layer management: it's what lets a real problem be told apart from expected, normal decline. A hen further along her cycle laying somewhat less than her peak isn't a problem to investigate — it's the curve doing exactly what it's supposed to.</p>"""),
    ("Lighting and the Nutrition Transition",
     """<h2>Lighting drives lay — and consistency matters as much as level</h2>
<p>Light stimulates egg laying. A gradually increasing lighting schedule as pullets approach point-of-lay is standard practice. Inconsistent or poorly-timed lighting is a common, overlooked cause of delayed or erratic lay onset — worth checking before assuming a nutritional or health cause. Light needs to STAY consistent through the laying period too, not just during the ramp-up: sudden changes in day length can trigger a production dip or an unplanned molt.</p>
<h2>Getting the calcium switch right</h2>
<p>Layer ration's sharply higher calcium content needs to start right at point-of-lay — not late. A hen still on grower feed once she starts laying draws calcium from her own skeleton to form shells, a cost that shows up in both shell quality and her own long-term skeletal health.</p>"""),
    ("Nest Boxes, Collection, and Molting",
     """<h2>Getting the physical setup right</h2>
<p>Roughly one nest box per four to five hens, kept clean, quiet, and dim, reduces floor-laid eggs and egg-eating behavior — a habit that starts once hens encounter a broken floor egg and, once established in a flock, is genuinely hard to eliminate.</p>
<h2>Why frequent collection matters beyond breakage</h2>
<p>Frequent egg collection reduces breakage and contamination, and — just as importantly — reduces the chance of egg-eating habit formation in the first place, tying directly back to the nest-box point above.</p>
<h2>Molting — a real tradeoff, not a default protocol</h2>
<p>Natural molt pauses lay after a full production cycle. Some operations use managed or induced molt to reset a flock for a second cycle — this carries real production-economics and welfare tradeoffs, and is worth a vet's specific input rather than applying a generic protocol without that conversation.</p>"""),
    ("Recognizing a Real Problem",
     """<h2>Gradual versus sudden — the distinction that matters most</h2>
<p>A gradual decline in egg production is normal, following the curve covered in the first module. A SUDDEN, sharp drop is different and warrants real investigation — this single distinction is most of what good layer troubleshooting actually comes down to.</p>
<h2>What a sudden drop points toward</h2>
<p>Infectious causes to consider: infectious bronchitis, Newcastle disease, and mycoplasmosis — each covered in their own courses elsewhere on this platform. Non-infectious causes: heat stress, lighting disruption, or a feed/water access problem. A sudden drop rarely has just one plausible explanation, which is exactly why it deserves a structured workup rather than a first guess.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for a specific flock. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does knowing the normal production curve matter for layer management?",
        "It's what lets a genuine problem be told apart from expected decline — a hen further along her cycle "
        "laying somewhat less than peak isn't itself a sign something is wrong.",
        "It lets a genuine problem be distinguished from the expected, normal decline later in a hen's cycle",
        "Egg production stays essentially flat throughout a hen's laying cycle with no real curve to understand",
    ),
    (
        "Why does light need to stay consistent through the whole laying period, not just during the ramp-up to point-of-lay?",
        "Sudden changes in day length during lay can trigger a production dip or an unplanned molt, not just "
        "affect when lay begins in the first place.",
        "Sudden day-length changes during lay can trigger a production dip or an unplanned molt",
        "Lighting consistency only matters before point-of-lay and has no effect once a hen is already laying",
    ),
    (
        "Why does delaying the switch to layer ration (with its higher calcium) past point-of-lay cause a real cost?",
        "A hen already laying but still on grower feed draws calcium from her own skeleton to form shells, "
        "affecting both shell quality and her own long-term skeletal health.",
        "The hen draws calcium from her own skeleton to form shells, affecting both shells and her skeletal health",
        "Feed timing at point-of-lay has no real effect on shell quality or the hen's own health",
    ),
    (
        "What is the key distinction that should guide whether a drop in egg production needs investigation?",
        "A gradual decline following the normal production curve is expected and not concerning; a SUDDEN, sharp "
        "drop is different and should prompt real investigation into infectious or non-infectious causes.",
        "Whether the drop is gradual (normal) or sudden and sharp (warrants real investigation)",
        "Any drop in production, gradual or sudden, should always be treated as an emergency requiring investigation",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Management of Laying Hens' — sixteenth of the poultry-only "
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
                organization=org, programme=programme, slug="management-of-laying-hens",
                defaults={
                    "title": "Management of Laying Hens",
                    "subtitle": "A sudden, sharp drop in egg production is never normal. A gradual one usually is "
                                 "— knowing the difference is most of what good layer management comes down to.",
                    "description": "<p>A 4-module continuing-education course on laying hen management — the "
                                    "normal production curve, lighting and the calcium/nutrition transition at "
                                    "point-of-lay, nest boxes/collection/molting decisions, and recognizing when a "
                                    "production drop genuinely warrants investigation.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Gradual decline is normal. Sudden decline is a real problem — know which is which",
                    "sales_subheadline": "4 modules on laying hen management — the production curve, lighting/"
                                          "nutrition timing, and recognizing a genuine production drop.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving layer operations\n"
                        "Practitioners troubleshooting a reported egg production drop\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Laying hen management CE for vets — production curve, lighting/nutrition "
                                         "timing, and recognizing a real production drop.",
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
                organization=org, name="Management of Laying Hens — Final Exam",
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
                title="Final Exam — Management of Laying Hens",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
