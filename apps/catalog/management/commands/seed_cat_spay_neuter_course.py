from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Eighth and final of the cat-coverage-gap-closing batch built so far
# (see seed_felv_fiv_course.py's header for the batch's overall
# context; vetfresh-6c says this brings cats to 11 total posts,
# matching dogs' and poultry's coverage, but more may come whenever
# Sam picks a new direction). Explicitly cross-references
# seed_cat_bite_abscess_course.py and seed_felv_fiv_course.py — the
# same neutering-reduces-fighting-behavior mechanism connects all
# three courses, matching how the source article itself framed it.

MODULES = [
    ("Benefits of Spaying and Neutering",
     """<h2>Spaying — eliminating real disease risk, and timing that matters</h2>
<p>Spaying eliminates pyometra risk entirely — a serious, potentially fatal uterine infection — along with ovarian and uterine cancers. SPAYING BEFORE THE FIRST HEAT CYCLE is specifically linked to significantly reduced lifetime mammary tumor risk. The protective benefit diminishes with each heat cycle that passes before spaying, so earlier timing is genuinely MORE protective, not merely equally effective whenever it eventually happens.</p>
<h2>Neutering — a dual behavioral and health benefit</h2>
<p>Neutering eliminates testicular cancer risk entirely, and significantly reduces roaming, territorial fighting, and urine-marking. This directly reduces cat bite abscess risk AND FIV transmission risk, since both are driven substantially by the same unneutered-male behavior — already established in this platform's own Cat Bite Abscesses and FeLV/FIV courses.</p>"""),
    ("Timing",
     """<h2>Traditional guidance versus current practice</h2>
<p>Traditional guidance called for spaying or neutering around 5-6 months of age. EARLY-AGE SPAY/NEUTER — as young as 8-12 weeks, if the kitten is healthy enough — is increasingly practiced and considered safe by major veterinary organizations.</p>
<h2>Where early-age timing matters most</h2>
<p>This is particularly relevant for shelter and community-cat management, where waiting risks the animal reaching sexual maturity before the procedure happens at all — undermining the entire point of the intervention. The right timing for an individual pet cat is a genuine conversation with a vet, factoring in the animal's health, breed, and the owner's realistic ability to prevent unplanned mating if the procedure is delayed.</p>"""),
    ("Common Misconceptions",
     """<h2>Weight gain isn't an inherent surgical consequence</h2>
<p>Spay or neuter surgery doesn't inherently cause weight gain. Reduced activity combined with unchanged feeding is what actually drives it — both manageable through portion control, not an inevitable outcome of the procedure itself.</p>
<h2>"One litter first" has no real veterinary basis</h2>
<p>The idea of letting a female cat have one litter before spaying has no real veterinary basis. If anything, earlier spaying — before the first heat cycle — is MORE protective against mammary tumors, directly contradicting the premise behind this common piece of folk advice.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own timing recommendation for an individual animal. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does spaying before a cat's first heat cycle provide more protection against mammary tumors than spaying later?",
        "The protective benefit diminishes with each heat cycle that passes before spaying, so earlier timing is "
        "genuinely more protective, not just equally effective whenever spaying eventually happens.",
        "The protective benefit against mammary tumors diminishes with each heat cycle before the spay is done",
        "Mammary tumor protection from spaying is identical regardless of how many heat cycles occur first",
    ),
    (
        "Why does neutering a male cat reduce both bite abscess risk and FIV transmission risk together, not just one?",
        "Both risks are driven substantially by the same unneutered-male fighting and roaming behavior, so "
        "reducing that behavior through neutering lowers exposure to both conditions at once.",
        "Both risks stem from the same unneutered-male fighting/roaming behavior, which neutering directly reduces",
        "Neutering only meaningfully affects bite abscess risk and has no real connection to FIV transmission",
    ),
    (
        "Why does early-age spay/neuter matter particularly for shelter and community-cat management?",
        "Waiting risks the animal reaching sexual maturity before the procedure happens at all, which "
        "undermines the entire purpose of the intervention in a population where follow-through can't be guaranteed.",
        "Waiting risks the animal reaching sexual maturity before the procedure ever actually happens",
        "Early-age spay/neuter carries no particular advantage in shelter settings compared to pet households",
    ),
    (
        "Why does the 'let her have one litter first' idea actually work against its own supposed benefit?",
        "It has no real veterinary basis, and if anything, spaying before the first heat cycle is MORE "
        "protective against mammary tumors — directly contradicting the premise behind the advice.",
        "Spaying before the first heat cycle is actually more protective, directly contradicting the advice's premise",
        "Having one litter before spaying genuinely does provide meaningful additional health protection to the cat",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Spaying and Neutering Cats: Timing and Benefits' — eighth and "
        "final of the cat-coverage-gap-closing batch built so far. Safe to re-run."
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
                organization=org, programme=programme, slug="spaying-neutering-cats-timing-benefits",
                defaults={
                    "title": "Spaying and Neutering Cats: Timing and Benefits",
                    "subtitle": "The \"let her have one litter first\" idea has no real veterinary basis — if "
                                 "anything, spaying before the first heat is more protective, not less.",
                    "description": "<p>A 3-module continuing-education course on spaying and neutering cats — "
                                    "real disease-prevention and behavioral benefits including the dual bite-"
                                    "abscess/FIV effect of neutering, current timing guidance including early-age "
                                    "spay/neuter, and common misconceptions worth correcting directly with owners.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "\"One litter first\" has no real basis — the opposite is actually true",
                    "sales_subheadline": "3 modules on cat spay/neuter — real benefits, current timing guidance, "
                                          "and correcting common owner misconceptions directly.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners counseling new owners on spay/neuter timing\n"
                        "Anyone working with shelters or community-cat programs on early-age protocols"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Cat spay/neuter CE for vets — real benefits, current timing guidance, "
                                         "and correcting common owner misconceptions.",
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
                organization=org, name="Spaying and Neutering Cats — Final Exam",
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
                title="Final Exam — Spaying and Neutering Cats",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
