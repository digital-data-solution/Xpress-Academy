from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Third of the new "Pet Owner Education" track (see
# seed_recognizing_vet_emergency_course.py's header for the
# categorization rationale and Programme details).

MODULES = [
    ("Life-Stage Feeding and Why Cats Aren't Small Dogs",
     """<h2>Growing animals need more than "enough" volume</h2>
<p>Puppies and kittens need higher protein, calorie, and calcium-phosphorus density relative to their body size than adults do. Adult-maintenance food underfeeds a growing animal even at a volume that looks like "enough" on the bowl — the issue is density, not just quantity.</p>
<h2>A cat is not a small dog, nutritionally</h2>
<p>Cats are obligate carnivores with real nutritional requirements dogs don't share. Taurine is the best-known example — cats can't sufficiently synthesize it themselves, and deficiency causes serious heart and eye disease. Feeding a cat long-term dog food is a real health risk, not just a lesser option to reach for in a pinch. Cats also have a naturally low thirst drive relative to their actual fluid needs, adapted to getting most of their moisture from prey in the wild — which is exactly why wet food and water encouragement matter more for cats than they do for dogs.</p>"""),
    ("Feeding Puppies and Kittens",
     """<h2>Small stomachs, higher metabolism</h2>
<p>Frequent small meals match a puppy or kitten's smaller stomach capacity and higher metabolic rate compared to an adult. A gradual transition to adult food over roughly 7-10 days, once the animal is age- and size-appropriate, avoids the digestive upset a sudden switch can cause.</p>
<h2>Large-breed puppies need their own formulation — a real exception</h2>
<p>Large-breed puppies need large-breed-formulated food specifically. Excess calcium and calories during rapid growth are linked to skeletal problems in these breeds — "feed more to grow big and strong" is genuinely the WRONG instinct for a giant-breed puppy, even though it feels intuitively right. This is one of the clearest places where good intentions and correct nutrition actually diverge.</p>"""),
    ("Adult Feeding and Common Mistakes",
     """<h2>Body condition beats the number on a scale</h2>
<p>Body condition scoring — feeling for ribs, checking the waist — is more reliable than weight alone, given how much frame and breed variation exists across dogs and cats. Treats should stay a small minority of daily calories, not an afterthought that quietly adds up.</p>
<h2>Free-feeding, and a real hidden cost</h2>
<p>Free-feeding works fine for some animals and contributes to obesity in others. Beyond weight management, portion control also makes an appetite change — often an early sign of illness — much easier to actually notice, a benefit that's easy to overlook when thinking about feeding purely in terms of weight.</p>
<h2>Table scraps — a real toxicity risk, not just extra calories</h2>
<p>Chocolate, grapes and raisins, onions and garlic, and xylitol are genuinely toxic to dogs and cats — this isn't a "moderation is fine" situation the way extra calories from a bland scrap might be. These specific foods carry real risk regardless of the amount given.</p>
<h2>A note on this course's limits</h2>
<p>This is general educational content for pet owners, not a substitute for a veterinarian's specific dietary guidance for your animal, especially one with an existing health condition.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does feeding a growing puppy or kitten adult-maintenance food at a normal-looking volume still underfeed them?",
        "Growing animals need higher protein, calorie, and calcium-phosphorus density relative to body size — the "
        "issue is nutrient density, not simply how much food is in the bowl.",
        "Growing animals need higher nutrient density relative to body size, not just a larger volume of adult food",
        "Adult-maintenance food and growth-formulated food are nutritionally identical regardless of density",
    ),
    (
        "Why is taurine specifically significant when explaining why a cat shouldn't be fed dog food long-term?",
        "Cats can't sufficiently synthesize taurine themselves, and deficiency causes serious heart and eye "
        "disease — a real nutritional requirement dogs don't share, not a minor formulation difference.",
        "Cats can't sufficiently self-synthesize taurine, and a deficiency causes serious heart and eye disease",
        "Taurine is equally important to both dogs and cats, so the distinction has no real practical significance",
    ),
    (
        "Why is 'feed more to grow big and strong' actually the wrong instinct for a large-breed puppy?",
        "Excess calcium and calories during rapid growth in these breeds are linked to real skeletal problems — "
        "large-breed puppies need a specifically formulated food, not simply more of a standard puppy food.",
        "Excess calcium and calories during rapid growth are linked to real skeletal problems in large breeds",
        "Large-breed puppies actually benefit from extra calcium and calories beyond what standard puppy food provides",
    ),
    (
        "Why are foods like chocolate, grapes, onions, and xylitol treated differently from ordinary table scraps?",
        "They're genuinely toxic to dogs and cats regardless of the amount given — unlike a bland scrap where "
        "moderation and portion size are the main concern, these specific foods carry real risk at any amount.",
        "They're genuinely toxic at essentially any amount, unlike ordinary scraps where portion size is the main issue",
        "These foods are only a concern in large quantities, similar to how extra calories from any scrap would be",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Nutrition Basics: Feeding Puppies, Kittens, and Adult Pets "
        "Correctly' — third course in the 'Pet Owner Education' track. Safe to re-run."
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
                # programmes — these are cross-promotion content too, sourced
                # from the same Vet Marketplace blog collaboration. Left off
                # the original get_or_create by oversight (defaulted to
                # WebhookLine.NONE), which meant these 5 courses published
                # without ever notifying Vet Marketplace's dashboard — see
                # apps/catalog/management/commands/fix_pet_owner_education_webhook_line.py
                # for the one-time retroactive fix.
                "webhook_line": Programme.WebhookLine.VET,
            },
        )
        if prog_created:
            self.stdout.write(self.style.SUCCESS(f"Created programme: {programme}"))

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="nutrition-basics-puppies-kittens-adults",
                defaults={
                    "title": "Nutrition Basics: Feeding Puppies, Kittens, and Adult Pets Correctly",
                    "subtitle": "A cat is not a small dog, nutritionally — feeding one like one is a real, "
                                 "avoidable health risk.",
                    "description": "<p>A 3-module guide for pet owners on nutrition basics — life-stage feeding "
                                    "and the real differences between cats and dogs, feeding puppies and kittens "
                                    "correctly including the large-breed-puppy exception, and adult feeding "
                                    "including real food-toxicity risks.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_published": False,
                    "sales_headline": "\"Feed more to grow big and strong\" is the wrong instinct for some puppies",
                    "sales_subheadline": "A free guide to feeding puppies, kittens, and adult pets correctly — "
                                          "including real food-toxicity risks worth knowing.",
                    "target_audience": (
                        "Any dog or cat owner\n"
                        "New puppy or kitten owners setting up a feeding routine for the first time\n"
                        "Large-breed puppy owners specifically"
                    ),
                    "not_for": "",
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Free guide for pet owners — life-stage feeding, large-breed-puppy "
                                         "nutrition, and real food-toxicity risks.",
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
                organization=org, name="Nutrition Basics — Final Check",
                description="Covers all 3 modules — must be passed to unlock the certificate.",
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
                title="Final Check — Nutrition Basics",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full guide. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final check."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
