from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Ninth of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("Internal Parasites",
     """<h2>Roundworms — the transmammary route that exempts no kitten</h2>
<p>Roundworms (Toxocara cati) are extremely common, and TRANSMAMMARY transmission through the mother's milk means even indoor-only kittens can be born infected. This single fact is exactly why routine kitten deworming is standard regardless of lifestyle — an indoor-only kitten still needs the standard early schedule, since infection can already be present before the kitten ever sets foot outside.</p>
<h2>Hookworms, tapeworms, and heartworm</h2>
<p>Hookworms are less significant in cats than in dogs, but can still cause anemia in heavy infections. Tapeworms (Dipylidium caninum) are acquired via ingesting infected fleas during grooming — which means tapeworm control is fundamentally linked to flea control, not a separate problem. Heartworm is less common in cats than dogs and presents differently: cats are a less natural host, so even a small worm burden can cause respiratory signs — "heartworm-associated respiratory disease" — and feline heartworm is genuinely underdiagnosed, since standard antigen testing is less reliable given the typically lower worm burdens seen in cats.</p>"""),
    ("External Parasites",
     """<h2>Fleas — the most common, and a vector in their own right</h2>
<p>Fleas are the most common external parasite, causing itching, hair loss, and anemia in heavy infestations. Beyond direct damage, fleas are the tapeworm vector already covered above, and can trigger flea allergy dermatitis from just one or two bites in sensitized cats — a disproportionate reaction relative to the actual flea burden.</p>
<h2>Ear mites</h2>
<p>Ear mites (Otodectes cynotis) cause head shaking, ear scratching, and a dark, crumbly discharge, especially in kittens and outdoor cats.</p>"""),
    ("Deworming Schedules",
     """<h2>Kittens — more frequent than adults, for a real reason</h2>
<p>Kittens should be dewormed starting around two to three weeks of age, repeated every two to three weeks until well past weaning — more frequent than adult deworming, given the transmammary route already covered that means infection can be present from birth.</p>
<h2>Adults — lifestyle matters, there's no single schedule</h2>
<p>Adult deworming frequency depends on lifestyle — indoor-only versus outdoor or hunting cats face genuinely different exposure risk, so no single generic schedule fits every cat. A fecal exam is a more precise guide than any blanket schedule, particularly for a cat whose actual exposure risk isn't well characterized.</p>
<h2>Flea control belongs alongside deworming</h2>
<p>Given the tapeworm-flea link already covered, flea control should run alongside deworming rather than being treated as a separate, optional add-on — deworming without addressing fleas leaves the tapeworm transmission route wide open.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for an individual cat. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does an indoor-only kitten still need the standard early deworming schedule?",
        "Transmammary transmission through the mother's milk means a kitten can already be born infected with "
        "roundworms, regardless of whether it's ever gone outside.",
        "Transmammary transmission through the mother's milk means a kitten can already be infected at birth",
        "Indoor-only kittens are exempt from routine deworming since they have no outdoor exposure risk",
    ),
    (
        "Why is tapeworm control described as fundamentally linked to flea control?",
        "Tapeworms are acquired via ingesting infected fleas during grooming, so deworming without addressing "
        "fleas leaves the transmission route wide open for reinfection.",
        "Tapeworms are acquired by ingesting infected fleas during grooming, making flea control part of tapeworm control",
        "Tapeworms and fleas are transmitted through entirely separate, unrelated routes",
    ),
    (
        "Why is feline heartworm considered genuinely underdiagnosed compared to canine heartworm?",
        "Cats are a less natural host with typically lower worm burdens, making the standard antigen test less "
        "reliable in cats than it is in dogs, where burdens are usually higher.",
        "Standard antigen testing is less reliable in cats given their typically lower worm burdens than dogs",
        "Feline heartworm is actually easier to detect than canine heartworm using the same standard tests",
    ),
    (
        "Why is a fecal exam described as a more precise guide for adult cat deworming than a blanket schedule?",
        "Adult deworming needs depend heavily on lifestyle (indoor-only vs. outdoor/hunting), so a fecal exam "
        "reflects an individual cat's actual exposure and burden rather than assuming one schedule fits every cat.",
        "It reflects an individual cat's actual parasite burden rather than assuming one schedule fits every cat",
        "A blanket schedule is always at least as precise as an individual fecal exam for any adult cat",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Common Feline Parasites and Deworming Schedules' — ninth of the "
        "mixed dogs/cats/livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="feline-parasites-deworming-schedules",
                defaults={
                    "title": "Common Feline Parasites and Deworming Schedules",
                    "subtitle": "An indoor-only kitten can still be born with roundworms — infection through the "
                                 "mother's milk means lifestyle doesn't exempt any kitten from the standard "
                                 "early deworming schedule.",
                    "description": "<p>A 3-module continuing-education course on feline parasites and deworming "
                                    "— internal parasites including the transmammary roundworm route and "
                                    "underdiagnosed feline heartworm, external parasites and the flea-tapeworm "
                                    "link, and deworming schedules that reflect real kitten and adult-lifestyle "
                                    "risk rather than one generic protocol.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "\"Indoor-only\" doesn't exempt a kitten from the standard deworming schedule",
                    "sales_subheadline": "3 modules on feline parasites — the transmammary route, flea-tapeworm "
                                          "link, and building real lifestyle-based deworming schedules.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners advising new kitten owners on early deworming timing\n"
                        "Anyone investigating unexplained respiratory signs in a cat that could reflect heartworm"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline parasites CE for vets — transmammary roundworms, flea-tapeworm "
                                         "link, and lifestyle-based deworming schedules.",
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
                organization=org, name="Common Feline Parasites and Deworming Schedules — Final Exam",
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
                title="Final Exam — Common Feline Parasites and Deworming Schedules",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
