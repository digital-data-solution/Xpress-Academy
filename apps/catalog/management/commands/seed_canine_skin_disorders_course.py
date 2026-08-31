from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Sixth of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("Sarcoptic Mange (Scabies)",
     """<h2>What it is, and a real household risk</h2>
<p>Sarcoptic mange is caused by the Sarcoptes scabiei mite. It's highly contagious dog-to-dog, and notably ZOONOTIC — it can cause a temporary, self-limiting itchy rash in people, since the mite can't complete its life cycle on human skin. That last detail matters: the human rash resolves on its own once the source is treated, but it's real enough to affect the whole household while active mange goes untreated.</p>
<h2>What you'll see, and how it's confirmed</h2>
<p>Intense itching — the most severe on this list of three conditions — along with hair loss and crusting, classically starting on the ears, elbows, and belly. Diagnosis is via skin scraping, though scraping can miss even genuine cases; response to treatment is sometimes used as supporting evidence when scraping comes back negative but the clinical picture still fits.</p>
<h2>Treatment — every contact dog, not just the affected one</h2>
<p>A specific anti-parasitic treats the mite. Given how contagious sarcoptic mange is, EVERY contact dog should be treated, not just the one showing symptoms — treating only the visibly affected dog in a multi-dog household routinely leads to reinfection from an untreated, silently-carrying companion.</p>"""),
    ("Demodectic Mange",
     """<h2>A normal resident that only causes disease when it overgrows</h2>
<p>Demodex mites are normal residents in small numbers on essentially every dog. Disease only occurs when the population grows out of control — in puppies, this is usually tied to a still-developing immune system; in adults, it points to an underlying illness or immunosuppression.</p>
<h2>Not contagious, unlike sarcoptic mange</h2>
<p>Demodectic mange is NOT significantly contagious, since it's an overgrowth of an organism the dog already carries rather than something newly acquired from another animal — a genuinely different transmission story from sarcoptic mange, worth keeping straight when advising an owner on whether other household pets are at risk.</p>
<h2>Localized versus generalized — a real diagnostic branch point</h2>
<p>The localized form, seen in puppies with just a few patches, often self-resolves as the immune system matures — usually not a cause for alarm. The generalized form in an ADULT dog is different and should prompt investigation for an UNDERLYING health problem, not just topical treatment of the visible mange itself.</p>"""),
    ("Dermatophytosis (Ringworm) and Telling the Three Apart",
     """<h2>Not a worm at all</h2>
<p>Despite the name, ringworm is a fungal infection (Microsporum or Trichophyton species), not a parasite. The classic presentation is circular, scaling hair loss, though the actual presentation varies more than the name suggests. It's genuinely ZOONOTIC and represents a real household hygiene concern.</p>
<h2>Diagnosis and why environmental treatment matters</h2>
<p>Fungal culture is the gold standard, though slow — days to weeks. A Wood's lamp fluoresces some but not all species, so a negative result under the lamp doesn't rule out ringworm. Treatment is topical or oral antifungal medication over several weeks PLUS environmental decontamination — fungal spores persist on bedding and carpet, and skipping the environmental step causes reinfection even after the skin itself clears.</p>
<h2>Telling all three apart</h2>
<p>Sarcoptic mange: intense itching dominant, contagious, mildly zoonotic. Demodectic mange: mild or absent itching, not contagious, and a generalized adult presentation means look for an underlying cause. Ringworm: variable itching, classic circles that aren't universal, genuinely zoonotic, culture-diagnosed, and needs environmental decontamination alongside treatment. Actual diagnosis matters more than appearance guessing — these three can look similar on the surface but need genuinely different diagnostics and treatment.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why should every contact dog be treated for sarcoptic mange, not just the one showing symptoms?",
        "Sarcoptic mange is highly contagious dog-to-dog, so treating only the visibly affected dog routinely "
        "leads to reinfection from an untreated companion that's silently carrying the mite.",
        "It's highly contagious, so an untreated companion dog can silently reinfect the one that was already treated",
        "Sarcoptic mange only ever affects one dog at a time in a multi-dog household",
    ),
    (
        "Why is generalized demodectic mange in an ADULT dog treated differently from the localized form in a puppy?",
        "The generalized adult form should prompt investigation for an underlying illness or immunosuppression, "
        "while the puppy localized form often self-resolves as the immune system matures.",
        "The generalized adult form should prompt investigation for an underlying health problem, unlike the puppy form",
        "Both forms carry an identical clinical significance regardless of the dog's age or the extent of the mange",
    ),
    (
        "Why is demodectic mange considered not significantly contagious, unlike sarcoptic mange?",
        "It's an overgrowth of an organism the dog already carries in small numbers, not something newly acquired "
        "from another animal — a genuinely different transmission story from sarcoptic mange.",
        "It results from overgrowth of an organism already present on the dog, rather than new transmission",
        "Demodectic mange spreads between dogs just as readily as sarcoptic mange does",
    ),
    (
        "Why does ringworm treatment need to include environmental decontamination, not just treating the dog's skin?",
        "Fungal spores persist on bedding and carpet, and skipping environmental decontamination allows "
        "reinfection even after the skin itself has cleared with topical or oral treatment.",
        "Fungal spores persist in the environment and can reinfect the dog even after its skin has cleared",
        "Ringworm resolves fully with skin treatment alone and never requires any environmental cleanup",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Common Skin Disorders in Dogs: Mange and Ringworm' — sixth of the "
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
                organization=org, programme=programme, slug="common-skin-disorders-in-dogs",
                defaults={
                    "title": "Common Skin Disorders in Dogs: Mange and Ringworm",
                    "subtitle": "Three conditions that can look similar on the surface but need three different "
                                 "diagnoses — and two of them can actually spread to the people in the household.",
                    "description": "<p>A 3-module continuing-education course on common canine skin disorders — "
                                    "sarcoptic mange and its zoonotic, highly contagious profile, demodectic mange "
                                    "and the localized-versus-generalized-adult distinction, and dermatophytosis "
                                    "(ringworm) plus a direct comparison telling all three apart.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Three skin conditions that look alike but need three different diagnoses",
                    "sales_subheadline": "3 modules on sarcoptic mange, demodectic mange, and ringworm — real "
                                          "differentiation, zoonotic risk, and getting treatment right for each.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners distinguishing similar-looking skin presentations in the clinic\n"
                        "Anyone advising households on zoonotic risk from a dog's skin condition"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Canine skin disorders CE for vets — sarcoptic mange, demodectic mange, "
                                         "and ringworm, told apart and treated correctly.",
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
                organization=org, name="Common Skin Disorders in Dogs — Final Exam",
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
                title="Final Exam — Common Skin Disorders in Dogs",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
