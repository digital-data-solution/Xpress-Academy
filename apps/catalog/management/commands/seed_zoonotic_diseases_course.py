from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Second of the new "Pet Owner Education" track (see
# seed_recognizing_vet_emergency_course.py's header for the
# categorization rationale and Programme details).

MODULES = [
    ("What Zoonotic Actually Means, and the Short List",
     """<h2>A small subset, not most of what you've read on this blog</h2>
<p>"Zoonotic" means a disease passes between animals and people. It's a real category worth knowing, but it's a genuinely SMALL subset of everything covered on this platform — not most of it. Most infectious diseases in pets don't cross to people at all, despite sounding alarming.</p>
<h2>The genuinely zoonotic conditions worth knowing</h2>
<p>Ringworm is readily transmissible and causes a similar circular rash in people as it does in pets. Sarcoptic mange can cause a temporary, self-limiting itchy rash in people, since the mite can't complete its life cycle on human skin — real, but short-lived. Rabies is the most serious by far, and has its own dedicated course on this platform given how different and urgent the response is. Newcastle disease, a poultry disease, can cause mild, self-limiting conjunctivitis with heavy occupational exposure — a low risk for an ordinary household.</p>"""),
    ("Precautions and What's Often Overestimated",
     """<h2>The precautions that cover most of the real risk</h2>
<p>Hand hygiene after handling animals, animal waste, or raw food covers a large share of real risk on its own. Prompt vet attention for a suspicious skin lesion — rather than home-treating a guess — matters given how similar-looking skin conditions can have very different real risk profiles, as covered in this platform's own Skin Disorders course. Extra caution is worth taking for pregnant, very young, elderly, or immunocompromised household members. Routine parasite control reduces zoonotic risk as a genuine side effect of normal pet care, not a separate task.</p>
<h2>What's often overestimated</h2>
<p>Canine parvovirus, feline panleukopenia, and most of the poultry and livestock diseases covered on this platform are NOT transmissible to people, despite sounding serious. It's worth being specific about this rather than treating every alarming-sounding animal disease as an equal human risk — that kind of blanket caution doesn't actually protect anyone, and can distract from the small, real list above.</p>
<h2>A note on this course's limits</h2>
<p>This is general educational content for pet owners, not medical advice. If you or a household member develops symptoms after animal contact, see a doctor rather than relying on this guide alone.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is it inaccurate to assume most pet diseases covered on this platform pose a real risk to people?",
        "Zoonotic diseases are a genuinely small subset of everything covered — most infectious pet diseases, "
        "including canine parvovirus and feline panleukopenia, don't cross to people at all.",
        "Zoonotic diseases are a small subset overall, and most pet infectious diseases don't cross to people",
        "The majority of infectious diseases covered on this platform are genuinely transmissible to people",
    ),
    (
        "Why is rabies treated as its own separate category rather than grouped with the other zoonotic conditions here?",
        "It's the most serious by far, with a genuinely different and more urgent response required — enough of "
        "a distinction to warrant its own dedicated course rather than a brief mention alongside milder conditions.",
        "It's the most serious by far and requires a genuinely different, more urgent response than the others",
        "Rabies is actually the mildest of the zoonotic conditions covered and needs the least urgent response",
    ),
    (
        "Why does routine parasite control count as zoonotic risk reduction, even though it's not framed as a human-health measure?",
        "It reduces zoonotic risk as a genuine side effect of normal pet care, since several parasites relevant to "
        "pet health also carry some human transmission risk when left unmanaged.",
        "It reduces zoonotic risk as a genuine side effect of care that's primarily aimed at the pet's own health",
        "Parasite control has no real connection to zoonotic risk and is unrelated to human health outcomes",
    ),
    (
        "Why does treating every alarming-sounding animal disease as an equal human risk actually work against real protection?",
        "It can distract attention from the small, genuinely real list of zoonotic conditions, diluting focus that "
        "would be better spent on the specific precautions that actually cover most real risk.",
        "Blanket alarm can distract from the small, genuinely real list, diluting focus on precautions that actually matter",
        "There's no real downside to treating every animal disease as an equal risk to household members",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Zoonotic Diseases Every Pet Owner Should Know' — second course in "
        "the 'Pet Owner Education' track. Safe to re-run."
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
                organization=org, programme=programme, slug="zoonotic-diseases-every-pet-owner-should-know",
                defaults={
                    "title": "Zoonotic Diseases Every Pet Owner Should Know",
                    "subtitle": "Most infectious diseases in pets don't cross to people at all, despite sounding "
                                 "alarming. Here's the actual short list worth knowing.",
                    "description": "<p>A 2-module guide for pet owners on zoonotic disease — the genuinely small "
                                    "list of conditions that pass between pets and people, the precautions that "
                                    "cover most real risk, and what's commonly overestimated.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_published": False,
                    "sales_headline": "The real short list — not every alarming-sounding disease is a human risk",
                    "sales_subheadline": "A free guide to the small, genuine list of zoonotic conditions and the "
                                          "precautions that actually cover most real risk.",
                    "target_audience": (
                        "Any dog or cat owner\n"
                        "Households with pregnant, very young, elderly, or immunocompromised members\n"
                        "Anyone who wants a clear, non-alarmist view of what's actually a human risk"
                    ),
                    "not_for": "",
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Free guide for pet owners — the real short list of zoonotic diseases "
                                         "and the precautions that actually matter.",
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
                organization=org, name="Zoonotic Diseases Every Pet Owner Should Know — Final Check",
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
                title="Final Check — Zoonotic Diseases Every Pet Owner Should Know",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full guide. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final check."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
