from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# First of a new "Pet Owner Education" track — the 5 general/cross-
# species topics closing out the original ~30-topic mixed-species
# batch (see seed_newcastle_disease_course.py and
# seed_canine_distemper_course.py for that batch's earlier headers).
#
# CATEGORIZATION CALL (vetfresh-6c explicitly flagged this as a
# judgment call, not a directive): these 5 are practical pet-owner
# guidance, not clinical CE for practicing vets — genuinely different
# in kind from every other course in this batch, which all assume
# veterinary training. Rather than force them into the existing
# Veterinary Continuing Education programme (VET audience, priced as
# professional CE), created a new "Pet Owner Education" programme
# (GENERAL audience) instead. Priced FREE, not because the content is
# less valuable, but because the actual purpose here is the same
# cross-promotion/reach goal that started this whole batch — these
# are the platform's most shareable, most broadly useful topics, and
# a paywall works against that goal in a way it doesn't for
# professional CE content.

MODULES = [
    ("True Emergencies — Go Immediately",
     """<h2>The signs that mean "right now," not "let's watch it"</h2>
<p>Difficulty breathing, or open-mouth breathing in a CAT specifically, is always urgent — this is genuinely different from a panting dog, which is often normal. Unproductive retching combined with a distended abdomen points to bloat (GDV), a true emergency covered in its own course on this platform. Uncontrolled bleeding, suspected poisoning, and collapse, unresponsiveness, or seizures lasting two or more minutes — or seizures that cluster — all need immediate attention.</p>
<h2>Signs that are easy to underestimate</h2>
<p>Straining to urinate with little or no output is a true emergency, especially in MALE CATS, where a urinary blockage can be fatal within 24-48 hours. Being hit by a vehicle needs a vet check EVEN IF the animal looks fine — internal injury isn't always visible from the outside. A snake bite, dystocia (30-60+ minutes of straining with no offspring delivered), a deep or penetrating chest or abdomen wound, sudden inability to stand or use a limb, and a suddenly painful or squinting eye round out this list — all genuine emergencies, even when the animal doesn't look as dramatically unwell as the word "emergency" might suggest.</p>"""),
    ("Urgent (Same-Day) and What Can Wait",
     """<h2>Urgent — needs a vet the same day</h2>
<p>Persistent vomiting or diarrhea lasting 24 or more hours, or that's bloody, or occurring in a young, old, or already-ill animal, needs same-day attention. Not eating or drinking for 24 or more hours, limping that isn't improving, visible pain, and — worth calling out specifically — unusual hiding all belong here. Cats hide illness far better than dogs, so sudden hiding behavior is itself a real signal, not just a personality quirk to shrug off. A fast-growing or painful lump also warrants same-day attention.</p>
<h2>What can genuinely wait</h2>
<p>A single mild vomiting or diarrhea episode in an otherwise bright, active animal, mild itching alone, a small, stable, longstanding lump, and slightly reduced appetite for less than a day with nothing else going on can generally wait for a routine appointment rather than an emergency visit.</p>
<h2>The one rule that covers everything else</h2>
<p>When unsure, call first — it costs nothing and beats guessing, especially for the hard-to-read emergencies (urinary blockage, internal bleeding, early bloat) that genuinely don't look dramatic in the first hour.</p>
<h2>A note on this course's limits</h2>
<p>This is general educational content for pet owners, not a substitute for an actual veterinarian's assessment of your specific animal. When in doubt, always call a vet rather than relying on this guide alone.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is open-mouth breathing in a cat considered a true emergency, unlike panting in a dog?",
        "It's genuinely different from a panting dog — open-mouth breathing in a cat is always urgent and reflects "
        "real respiratory distress, not a normal cooling behavior the way panting often is in dogs.",
        "Open-mouth breathing in a cat is always urgent, unlike a panting dog which is often perfectly normal",
        "Open-mouth breathing means the same thing in cats and dogs, and neither is more urgent than the other",
    ),
    (
        "Why does straining to urinate with little output count as a true emergency specifically in male cats?",
        "A urinary blockage in a male cat can be fatal within 24-48 hours, making this a true emergency rather "
        "than something that can wait for a routine appointment.",
        "A urinary blockage in a male cat can be fatal within just 24-48 hours if not addressed promptly",
        "Straining to urinate is never a serious concern in cats of either sex and can safely wait",
    ),
    (
        "Why does an animal that's been hit by a vehicle need a vet check even if it looks fine afterward?",
        "Internal injury isn't always visible from the outside — an animal can look outwardly normal while still "
        "having serious internal damage that only a proper exam would catch.",
        "Internal injury isn't always visible from the outside, even when the animal appears outwardly normal",
        "An animal that looks fine immediately after being hit by a vehicle can be assumed to be genuinely unharmed",
    ),
    (
        "Why is sudden hiding behavior in a cat treated as a real signal rather than dismissed as personality?",
        "Cats hide illness far better than dogs, so a cat that suddenly starts hiding may actually be "
        "communicating real illness or discomfort, not simply having an off day.",
        "Cats hide illness far better than dogs, so sudden hiding can itself be a meaningful sign of illness",
        "Hiding behavior in cats is purely a personality trait with no connection to underlying health",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Recognizing a Veterinary Emergency: When to Rush In, When to Wait' "
        "— first course in the new 'Pet Owner Education' track. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, prog_created = Programme.objects.get_or_create(
            organization=org, slug="pet-owner-education",
            defaults={
                "title": "Pet Owner Education",
                "audience": Audience.GENERAL,
                "description": "Practical, plain-language guidance for pet owners — recognizing emergencies, "
                                "nutrition, vaccination timing, zoonotic risk, and parasite prevention. Distinct "
                                "from the Veterinary Continuing Education programme, which assumes veterinary "
                                "training.",
                # Same VET destination as the Veterinary CE and Dog Breeding
                # programmes — see seed_pet_nutrition_basics_course.py's own
                # comment here for the oversight this corrects.
                "webhook_line": Programme.WebhookLine.VET,
            },
        )
        if prog_created:
            self.stdout.write(self.style.SUCCESS(f"Created programme: {programme}"))

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="recognizing-a-veterinary-emergency",
                defaults={
                    "title": "Recognizing a Veterinary Emergency: When to Rush In, When to Wait",
                    "subtitle": "Cats hide illness far better than dogs, and some of the most dangerous "
                                 "emergencies don't look dramatic in the first hour.",
                    "description": "<p>A 2-module guide for pet owners on recognizing true veterinary emergencies "
                                    "— what needs immediate attention, what needs a same-day vet visit, and what "
                                    "can genuinely wait for a routine appointment.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_published": False,
                    "sales_headline": "Know the difference before you're standing in it at 11pm",
                    "sales_subheadline": "A free guide to true emergencies, same-day concerns, and what can "
                                          "genuinely wait for a routine vet visit.",
                    "target_audience": (
                        "Any dog or cat owner\n"
                        "New pet owners who haven't yet had to make an emergency-or-not judgment call\n"
                        "Anyone who wants a clear reference before they actually need it"
                    ),
                    "not_for": "",
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Free guide for pet owners — recognizing true emergencies vs. same-day "
                                         "concerns vs. what can wait.",
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
                organization=org, name="Recognizing a Veterinary Emergency — Final Check",
                description="Covers both modules — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.EASY,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course,
                title="Final Check — Recognizing a Veterinary Emergency",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full guide. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final check."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
