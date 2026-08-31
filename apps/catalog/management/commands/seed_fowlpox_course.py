from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A hardy DNA virus with an unusual transmission route</h2>
<p>Fowlpox is caused by fowlpox virus (FPV), genus Avipoxvirus — a large DNA virus that is unusually hardy outside the host, capable of surviving extended periods in dried skin scabs and contaminated litter.</p>
<h2>Mosquitoes, not the flock itself, drive most spread</h2>
<p>Transmission is mainly mechanical, via mosquitoes and other biting insects carrying virus from lesions on one bird to the next, plus direct contact through skin breaks. This gives fowlpox a seasonal, insect-activity-linked pattern rather than the pure bird-to-bird spread seen in diseases like Newcastle disease. All ages are susceptible, and the virus's hardy dried scabs mean a house can remain infectious well after the original case has clinically healed.</p>"""),
    ("Clinical Findings",
     """<h2>Two forms, two very different levels of concern</h2>
<p>The cutaneous ("dry pox") form produces wart-like nodules on the comb, wattles, face, and legs — progressing from papules to yellowish nodules to dark, crusty scabs that heal over several weeks. This form is usually mild and, while it looks alarming, rarely threatens the bird directly.</p>
<h2>The diphtheritic form is the one that matters clinically</h2>
<p>The diphtheritic ("wet pox") form produces yellowish-white plaques on the mucous membranes of the mouth, pharynx, esophagus, and trachea. Unlike the cutaneous form, this can interfere with eating and breathing directly — a real mortality risk that the cutaneous form simply doesn't carry.</p>"""),
    ("Diagnosis",
     """<h2>Cutaneous form — usually straightforward</h2>
<p>The cutaneous form is usually recognizable from lesion appearance alone, given its distinctive progression from papule to scab on the comb, wattles, and face.</p>
<h2>Diphtheritic form — worth confirming</h2>
<p>The diphtheritic form benefits from histopathology, looking for Bollinger bodies, or PCR confirmation, given how much more consequential a misdiagnosis would be. Key differentials for the diphtheritic form specifically: vitamin A deficiency, infectious laryngotracheitis, trichomoniasis, and candidiasis — all of which can produce a broadly similar oral/pharyngeal picture.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment differs sharply by form</h2>
<p>There is no antiviral treatment. The cutaneous form resolves on its own. The diphtheritic form may need careful membrane removal under veterinary guidance, given the real risk to eating and breathing it carries.</p>
<h2>Control — insect control is the central measure</h2>
<p>Unlike most poultry diseases covered on this platform, insect control is THE central control measure for fowlpox — reducing standing water and mosquito breeding sites directly interrupts the dominant transmission route. Extended cleaning and downtime are also warranted given the virus's environmental hardiness described earlier.</p>
<h2>Prevention — a highly effective, standard vaccine</h2>
<p>A live vaccine given by the wing-web stab method is highly effective and standard practice. A visible "take" — a small scab forming at the vaccination site — confirms the vaccine was administered correctly and the bird responded, a useful practical check that most other poultry vaccines don't offer as directly.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does fowlpox show a seasonal, insect-activity-linked pattern rather than pure bird-to-bird spread?",
        "Transmission is mainly mechanical, via mosquitoes and other biting insects carrying virus from lesions on "
        "one bird to another — so spread tracks insect activity rather than direct flock contact alone.",
        "Transmission is mainly mechanical, carried by mosquitoes and other biting insects between birds",
        "Fowlpox spreads exclusively through direct bird-to-bird contact with no insect involvement at all",
    ),
    (
        "Why is the diphtheritic ('wet pox') form of fowlpox considered more clinically serious than the cutaneous form?",
        "It produces plaques on the mucous membranes of the mouth, pharynx, esophagus, and trachea that can "
        "interfere with eating and breathing directly — a real mortality risk the cutaneous form doesn't carry.",
        "It can interfere directly with eating and breathing, unlike the generally mild cutaneous form",
        "Both forms carry an identical level of mortality risk to the affected bird",
    ),
    (
        "Why is insect control described as THE central control measure for fowlpox, unlike most other poultry diseases?",
        "Because mosquitoes and biting insects are the dominant mechanical transmission route for this specific "
        "virus, reducing their breeding sites directly interrupts how the disease actually spreads.",
        "Mosquitoes are the dominant transmission route here, unlike most other poultry diseases on this platform",
        "Insect control has no meaningful effect on fowlpox spread compared to standard biosecurity alone",
    ),
    (
        "What does a visible 'take' (small scab) at the wing-web vaccination site actually confirm?",
        "That the vaccine was administered correctly and the bird responded to it — a practical, visible check on "
        "vaccination success that most other poultry vaccines don't offer as directly.",
        "That the vaccine was correctly administered and the bird's immune system responded to it",
        "A visible take indicates the vaccination failed and the bird should be revaccinated",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Fowlpox in Chickens and Turkeys' — fifth of the poultry-only "
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
                organization=org, programme=programme, slug="fowlpox-in-chickens-and-turkeys",
                defaults={
                    "title": "Fowlpox in Chickens and Turkeys",
                    "subtitle": "Two forms with very different stakes — and the one poultry disease where insect "
                                 "control, not biosecurity alone, is the central defense.",
                    "description": "<p>A 4-module continuing-education course on fowlpox — etiology and its "
                                    "unusually hardy DNA virus, the sharp clinical difference between the "
                                    "cutaneous and diphtheritic forms, diagnosis, and treatment/control/prevention "
                                    "centered on insect control and the standard wing-web vaccine.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Alarming to look at, usually mild — until it isn't",
                    "sales_subheadline": "4 modules on fowlpox — the two clinical forms, diagnosis, and why insect "
                                          "control is the real defense here, not biosecurity alone.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners distinguishing cutaneous from diphtheritic presentations in the field\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Fowlpox CE for vets — cutaneous vs. diphtheritic forms, diagnosis, and "
                                         "insect-control-centered prevention.",
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
                organization=org, name="Fowlpox in Chickens and Turkeys — Final Exam",
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
                title="Final Exam — Fowlpox in Chickens and Turkeys",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
