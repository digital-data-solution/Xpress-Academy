from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Twentieth and final of the poultry-only ~20-topic batch built so
# far (see seed_mycoplasmosis_poultry_course.py's header for context;
# vetfresh-6c says this closes the batch, but Sam may send more later).

MODULES = [
    ("Egg Binding — A Genuine Emergency",
     """<h2>What's happening and why</h2>
<p>Egg binding is when a hen is unable to pass a fully formed egg, which becomes lodged in the oviduct or cloaca. Causes include calcium deficiency, obesity, an unusually large first egg, oviduct infection or inflammation (salpingitis, sometimes linked to colibacillosis, covered in its own course on this platform), or simple exhaustion in older or overworked hens.</p>
<h2>Recognizing it, and why timing matters</h2>
<p>Signs include straining, a distended abdomen, reluctance to move, tail pumping, and a visible bulge at the vent. This is a GENUINE EMERGENCY — untreated, it can be fatal within one to two days, from organ pressure or an internal breakage that leads to peritonitis. Gentle warm-water soaking and lubrication can help mild cases, but a genuinely stuck egg or a visibly distressed hen needs a vet promptly, not prolonged attempts at home.</p>"""),
    ("Prolapse",
     """<h2>How it happens</h2>
<p>Straining — often from egg binding itself, or from an unusually large or fast-laid egg — pushes oviduct tissue out through the vent.</p>
<h2>Why immediate separation matters more than the prolapse itself</h2>
<p>Prolapsed tissue attracts "vent pecking" from other hens in the flock, which can escalate to severe injury or death. A PROLAPSED HEN NEEDS IMMEDIATE SEPARATION from the rest of the flock — flockmates are often the bigger immediate threat, more urgent to address than the prolapse itself in the first few minutes. Mild cases may be gently cleaned and reduced by an experienced handler, but this is best vet-assessed given real injury and infection risk, and a genuine risk of recurrence.</p>"""),
    ("Soft/Thin Shells and Internal Laying",
     """<h2>Soft or thin shells — usually nutrition, but not always</h2>
<p>Most often a calcium or vitamin D3 supply-or-absorption problem, but worth considering other causes too: infections (infectious bronchitis is a well-documented cause of persistent poor shell quality, even after apparent recovery — a real connection to that course on this platform), heat stress (which reduces shell-gland calcium deposition efficiency, as covered in the Heat Stress course), or simple hen age. An occasional soft egg isn't concerning. A FLOCK-WIDE, PERSISTENT pattern is different, and deserves investigation as a nutrition, disease, or heat-stress issue.</p>
<h2>Internal laying and egg peritonitis — hard to catch early</h2>
<p>Internal laying happens when an egg or ovulated yolk is released into the abdominal cavity instead of the oviduct, or when an infection tracks into the reproductive tract — connecting directly to the salpingitis/egg peritonitis form of colibacillosis covered elsewhere on this platform. This is a serious, often fatal internal infection. Signs include depression and reduced or stopped lay, with a distended abdomen from fluid and inflammation. It can progress to death with few external signs, making it genuinely one of the harder reproductive problems to catch early.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for an individual bird. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is untreated egg binding considered a genuine emergency rather than something to monitor?",
        "It can be fatal within one to two days from organ pressure or an internal breakage leading to "
        "peritonitis — a short, real timeline that doesn't allow for a wait-and-see approach.",
        "It can become fatal within one to two days from organ pressure or a resulting internal infection",
        "Egg binding resolves on its own in nearly all cases within a few days without intervention",
    ),
    (
        "Why does a prolapsed hen need immediate separation from the rest of the flock as the first priority?",
        "Prolapsed tissue attracts vent pecking from other hens, which can escalate to severe injury or death — "
        "often a more urgent, immediate threat than the prolapse itself in the first few minutes.",
        "Prolapsed tissue attracts vent pecking from flockmates, which can escalate to severe injury or death",
        "Separation is a lower priority than immediately attempting to reduce the prolapse on-site",
    ),
    (
        "Why should a flock-wide, persistent pattern of soft or thin shells be investigated, even though an occasional soft egg isn't concerning?",
        "A persistent flock-wide pattern points to a real underlying cause — nutrition, infection (like infectious "
        "bronchitis), or heat stress — rather than the normal, occasional variation seen with a single soft egg.",
        "A persistent, flock-wide pattern signals a real underlying cause rather than normal occasional variation",
        "Soft or thin shells, occasional or persistent, never warrant any further investigation",
    ),
    (
        "Why is egg peritonitis described as one of the harder reproductive problems to catch early?",
        "It can progress toward death with relatively few external signs beyond depression and reduced lay, "
        "unlike egg binding or prolapse, which both present with more immediately visible signs.",
        "It can progress toward death with relatively few visible external signs along the way",
        "Egg peritonitis always presents with dramatic, unmistakable external signs well before it becomes serious",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Egg Production Problems: Prolapse, Egg-Bound Hens, and Soft-Shelled "
        "Eggs' — twentieth of the poultry-only ~20-topic Vet-blog cross-promotion "
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
                organization=org, programme=programme, slug="egg-production-problems",
                defaults={
                    "title": "Egg Production Problems: Prolapse, Egg-Bound Hens, and Soft-Shelled Eggs",
                    "subtitle": "An egg-bound hen is a real emergency. A prolapsed one needs separating from the "
                                 "flock immediately — the pecking that follows is often the bigger danger.",
                    "description": "<p>A 3-module continuing-education course on layer reproductive emergencies "
                                    "— egg binding and its real emergency timeline, prolapse and why immediate "
                                    "flock separation matters more than the prolapse itself, and soft/thin shells "
                                    "plus the harder-to-catch internal laying and egg peritonitis.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "The flockmates are often the bigger immediate threat, not the prolapse itself",
                    "sales_subheadline": "3 modules on layer reproductive problems — egg binding, prolapse, and "
                                          "the harder-to-catch internal laying and egg peritonitis.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving layer operations\n"
                        "Practitioners handling a reproductive emergency call in real time\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Layer reproductive emergencies CE for vets — egg binding, prolapse, and "
                                         "internal laying/egg peritonitis.",
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
                organization=org, name="Egg Production Problems — Final Exam",
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
                title="Final Exam — Egg Production Problems",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
