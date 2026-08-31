from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifth and final of the new "Pet Owner Education" track built so far
# (see seed_recognizing_vet_emergency_course.py's header for the
# categorization rationale and Programme details; vetfresh-6c says
# this closes the original ~30-item mixed-species list, but more may
# come whenever Sam picks a new direction).

MODULES = [
    ("Why Prevention Beats Treatment Here Specifically",
     """<h2>Real biological reasons, not just cost</h2>
<p>Several parasites and parasite-borne diseases covered on this platform carry real treatment risk or limited options once advanced. Heartworm treatment needs strict exercise restriction and carries genuine risk during the treatment process itself, already covered in its own course. Ehrlichiosis becomes harder to treat successfully once chronic bone marrow damage has already occurred. Histomoniasis treatment is outright limited in many countries today. On every one of these, the prevention side is dramatically simpler than the treatment side — this isn't a cost argument, it's a biological one.</p>
<h2>Indoor lifestyle reduces risk — it doesn't eliminate it</h2>
<p>Several parasites covered on this platform complete their entire life cycle indoors — red mite in poultry housing, the brown dog tick in homes and kennels, fleas in carpet and bedding. "Indoor pet" is a real risk reducer, not a guarantee of zero risk, and treating it as a guarantee is a genuine, avoidable mistake.</p>"""),
    ("Deworming and Flea/Tick Control",
     """<h2>Deworming — young animals need more frequent attention</h2>
<p>Puppies and kittens need a MORE frequent early deworming schedule than adults, given transmammary transmission — an indoor lifestyle doesn't exempt a young animal from this, the same point already made in this platform's own puppy and kitten courses. Adult deworming frequency should reflect actual lifestyle and risk, ideally guided by a fecal test rather than a blanket schedule applied to every animal regardless of its real exposure.</p>
<h2>Flea and tick control — year-round, not seasonal, in warm climates</h2>
<p>In warm climates, flea and tick control should run year-round rather than seasonally — fleas and the brown dog tick can complete their life cycles indoors, making "it's not tick season" a much less reliable assumption here than it would be in a temperate climate with a real winter die-off. Environmental treatment — bedding, cracks, the home itself — matters alongside treating the animal directly. Treating the pet alone while the environment stays infested is a common, avoidable reason infestations recur, the same principle already established for poultry red mite and canine ehrlichiosis in their own courses.</p>"""),
    ("Heartworm Prevention and Building a Real Routine",
     """<h2>Heartworm — a genuinely different risk model</h2>
<p>Heartworm prevention should be monthly, ideally YEAR-ROUND. It's mosquito-borne only, with no direct animal-to-animal transmission, so risk depends entirely on mosquito exposure, not on contact with other pets — a genuinely different risk model from most of the other parasites covered in this guide, worth keeping straight.</p>
<h2>One coordinated routine, not separate ad hoc decisions</h2>
<p>A vet-set schedule combining vaccination timing, routine deworming, and monthly flea/tick/heartworm prevention together — treated as one coordinated routine rather than a series of separate, ad hoc decisions — is what actually works in practice. Routine fecal exams plus annual heartworm and tick-disease screening catch problems before visible illness appears, the same "test, don't guess" principle already established for worm burden in poultry.</p>
<h2>A note on this course's limits</h2>
<p>This is general educational content for pet owners, not a substitute for a vet-set preventive schedule tailored to your specific animal, lifestyle, and local disease risk.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is prevention emphasized over treatment for parasites like heartworm and ehrlichiosis specifically?",
        "There are real biological reasons — heartworm treatment carries genuine risk during the process itself, "
        "and ehrlichiosis becomes harder to treat once chronic damage has occurred, not just a cost consideration.",
        "Real biological factors, not cost alone, make prevention dramatically simpler than treatment for these conditions",
        "Prevention is emphasized purely because it's cheaper than treatment, with no underlying biological reason",
    ),
    (
        "Why is 'indoor pet' not the same as 'zero parasite risk'?",
        "Several parasites — red mite, the brown dog tick, fleas — can complete their entire life cycle indoors, "
        "so an indoor lifestyle reduces exposure without eliminating the risk entirely.",
        "Several relevant parasites can complete their entire life cycle indoors, so indoor life reduces but doesn't eliminate risk",
        "Indoor pets face no meaningful parasite exposure risk whatsoever compared to those with outdoor access",
    ),
    (
        "Why does treating a pet for fleas or ticks without also treating the home environment often fail to resolve an infestation?",
        "These parasites can live in the environment itself — bedding, cracks, carpet — so an infested home can "
        "simply reinfest a treated animal unless the environment is treated too, the same pattern seen with poultry red mite.",
        "The parasites can live in the environment itself, so an untreated home can reinfest an already-treated pet",
        "Treating the pet alone is always fully sufficient to resolve any flea or tick infestation permanently",
    ),
    (
        "Why does heartworm risk depend on mosquito exposure rather than contact with other pets?",
        "It's transmitted only by mosquito bite with no direct animal-to-animal transmission, making its risk "
        "model genuinely different from most of the other contact-transmitted parasites covered in this guide.",
        "It's transmitted only by mosquito bite, with no direct animal-to-animal transmission route at all",
        "Heartworm actually spreads primarily through direct contact between pets, similar to fleas or ticks",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Parasite Prevention: Deworming and Tick/Flea Control Done Right' "
        "— fifth and final course in the 'Pet Owner Education' track built so far. "
        "Safe to re-run."
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
                organization=org, programme=programme, slug="parasite-prevention-deworming-flea-tick",
                defaults={
                    "title": "Parasite Prevention: Deworming and Tick/Flea Control Done Right",
                    "subtitle": "Indoor lifestyle reduces parasite risk — it doesn't eliminate it. Several "
                                 "parasites on this blog complete their entire life cycle indoors.",
                    "description": "<p>A 3-module guide for pet owners on parasite prevention — the real "
                                    "biological reasons prevention beats treatment, deworming and flea/tick "
                                    "control including year-round timing in warm climates, and heartworm "
                                    "prevention plus building one coordinated preventive routine.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_published": False,
                    "sales_headline": "\"Indoor pet\" reduces parasite risk — it doesn't erase it",
                    "sales_subheadline": "A free guide to deworming, flea/tick control, and heartworm prevention "
                                          "— built as one coordinated routine, not separate ad hoc decisions.",
                    "target_audience": (
                        "Any dog or cat owner\n"
                        "Owners of indoor-only pets who assume that fully removes parasite risk\n"
                        "Anyone wanting one coordinated preventive routine instead of scattered decisions"
                    ),
                    "not_for": "",
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Free guide for pet owners — deworming, flea/tick control, and heartworm "
                                         "prevention as one coordinated routine.",
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
                organization=org, name="Parasite Prevention — Final Check",
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
                title="Final Check — Parasite Prevention",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full guide. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final check."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
