from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course

# Real quiz questions per module (2-8 — module 1's already exist from
# seed_demo_course) plus a final exam spanning the whole course. Same
# format as the module 1 questions the seed command already writes:
# one stem, one explanation, one correct choice, one plausible wrong
# one — simple, but genuinely testing whether the module's actual
# content was understood, not trivia.

MODULE_QUESTIONS = {
    2: [
        (
            "A breeder mates her bitch the moment she first notices standing heat. What's the real risk?",
            "Standing heat can start before ovulation actually happens. Mating on the first visible "
            "sign alone risks missing the real fertile window — exactly the timing failure that gets "
            "healthy bitches wrongly labelled infertile.",
            "The fertile window may not have opened yet — visible signs and ovulation don't happen on the same day",
            "There's no risk — standing heat always means she's ovulating that same day",
        ),
        (
            "What does progesterone testing actually tell a breeder?",
            "A progesterone blood test tracks the hormone surge that triggers ovulation, letting a vet "
            "pin down the fertile window precisely rather than relying on visible signs alone.",
            "Roughly when ovulation is happening, so mating can be timed precisely",
            "Whether the bitch is already pregnant",
        ),
    ],
    3: [
        (
            "A natural mating results in a long tie between the two dogs. What should the breeder do?",
            "A tie — the dogs staying physically locked together, often 10-30 minutes or more — is "
            "normal canine reproductive biology. Trying to force a separation is the wrong move.",
            "Leave them be — this is normal and shouldn't be forced apart",
            "Separate them immediately, since a long tie means something has gone wrong",
        ),
        (
            "Why does the course caution against always using the most popular, most-used stud in a breed?",
            "Heavy use of one popular sire spreads his genes — including any hidden faults — "
            "disproportionately through the whole breed population, a real, documented issue.",
            "Because his genes, hidden faults included, spread disproportionately fast through the breed population",
            "Because popular studs are always overpriced compared to less popular ones",
        ),
    ],
    4: [
        (
            "A breeder wants to switch her pregnant bitch to a dewormer she's used before, without her vet. What's the right call?",
            "Not everything safe for a non-pregnant dog is safe during pregnancy. No medication, "
            "dewormer, or supplement should be given during pregnancy without checking with a vet first.",
            "Check with the vet first — pregnancy changes what's safe, even for something used before",
            "It's fine, since she's used it before without any problems",
        ),
        (
            "Roughly how is the 63-day gestation calendar counted?",
            "Average gestation is about 63 days from ovulation, not from the mating date — the two can "
            "differ by a few days, which is why accurate heat-cycle timing (Module 2) matters here too.",
            "From ovulation, not necessarily the mating date",
            "From the very first day any sign of heat appeared",
        ),
    ],
    5: [
        (
            "A bitch has been straining hard for 45 minutes with no puppy delivered. What should the breeder do?",
            "Strong, visible straining for more than 30-60 minutes with no puppy delivered is one of the "
            "clear red flags in this course — it means calling the vet now, not waiting to see what happens.",
            "Call the vet now — this is a red-flag sign of possible dystocia",
            "Wait another hour or two, since first labours often take a while",
        ),
        (
            "What is dystocia?",
            "Dystocia is difficult or obstructed labour, which can be caused by an oversized puppy, poor "
            "positioning, or other factors — sometimes resolved only by a caesarean, which the course "
            "frames as a normal outcome for some breeds and dogs, not a failure.",
            "Difficult or obstructed labour that sometimes requires a caesarean",
            "The normal, expected discomfort every bitch feels during labour",
        ),
    ],
    6: [
        (
            "Why is getting every puppy nursing within the first few hours of birth so important?",
            "Colostrum carries antibodies a newborn can only absorb efficiently in roughly the first "
            "12-24 hours of life — after that window closes, that protection is largely lost.",
            "Colostrum's antibody protection can only be absorbed well in a short early window after birth",
            "It's mainly about helping the puppies gain weight faster in the first week",
        ),
        (
            "A 2-day-old puppy is cold to the touch and hasn't nursed in hours. What's the correct first step?",
            "Warm the puppy gradually before attempting to feed it — a cold puppy can't digest food "
            "properly, so feeding first can make things worse, not better.",
            "Warm the puppy gradually first, then reassess feeding",
            "Feed it right away to give it energy to warm up on its own",
        ),
    ],
    7: [
        (
            "Why does the \"cold chain\" matter for vaccines in a Nigerian kennel context?",
            "Vaccines only work if stored correctly at every step. A vaccine left warm too long during "
            "transport or storage may simply not protect the puppy, even if given exactly on schedule "
            "— a real, practical risk where power supply is unreliable.",
            "A vaccine that wasn't kept properly cold may not actually protect the puppy, even if given on schedule",
            "Cold storage only affects how long a vaccine can be kept before opening, nothing else",
        ),
        (
            "Why quarantine a new dog before mixing it with the rest of the kennel?",
            "A period of separation for any new arrival — bought, rescued, or returning from a stud "
            "visit or show — is one habit that prevents a large share of real kennel disease outbreaks.",
            "It reduces the risk of introducing a disease the new dog is incubating but not yet showing signs of",
            "It's mainly a formality with little real effect on disease spread",
        ),
    ],
    8: [
        (
            "Why does the course recommend costing a litter honestly before pricing puppies?",
            "Breeders who skip properly costing stud fees, vet care, feed, and a buffer for things going "
            "wrong often discover after the fact that a litter they assumed was profitable barely broke even.",
            "Because skipping this step often means only discovering after the fact that the litter barely broke even",
            "Because Nigerian buyers always negotiate down from the listed price anyway",
        ),
        (
            "What's the main real benefit of screening buyers before selling a puppy?",
            "A good buyer conversation is the single biggest thing a breeder can do to reduce how many "
            "of their puppies end up abandoned or in poor homes later — not about being difficult.",
            "It meaningfully reduces the chance a puppy ends up abandoned or in a poor home later",
            "It mainly helps the breeder negotiate a higher price",
        ),
    ],
}

FINAL_EXAM_QUESTIONS = [
    (
        "What's the actual problem with mating a bitch purely on the first visible sign of standing heat?",
        "Visible signs of heat don't reliably mark the exact fertile day — ovulation can happen days "
        "after standing heat begins, and timing failure is the most common cause of a \"failed\" mating.",
        "It risks missing the real fertile window, since visible signs and ovulation aren't the same day",
        "There's no problem — standing heat always means peak fertility that same day",
    ),
    (
        "What's the key difference between line-breeding and inbreeding, as this course defines them?",
        "Line-breeding mates relatives sharing a distant common ancestor, deliberately concentrating "
        "wanted traits. Inbreeding takes this too close (siblings, parent-offspring) and concentrates "
        "everything — including hidden faults — much faster.",
        "Line-breeding uses distant relatives deliberately; inbreeding mates much closer relatives and concentrates everything faster",
        "They're the same practice, just different names for it",
    ),
    (
        "A stud has been used across dozens of litters because he's a big winner. What real concern does this raise?",
        "This is the popular-sire problem — heavy use of one dog spreads his genes, hidden faults "
        "included, disproportionately through the whole breed population.",
        "His hidden faults, if any, are now spreading through the breed population faster than normal",
        "There's no concern — a proven, popular stud is always the safest choice",
    ),
    (
        "Why should medication decisions during pregnancy always go through a vet first?",
        "Not everything safe for a non-pregnant dog is safe during pregnancy — this is one of the "
        "clearest lines in the course between a breeder's own judgement and a vet's decision.",
        "Because pregnancy changes what's safe, even for routine medications or dewormers",
        "Because it's only a legal formality with little real medical basis",
    ),
    (
        "A bitch has strained hard for over 45 minutes with no puppy delivered. What does the course say to do?",
        "This is an explicit red flag — call the vet immediately rather than wait, since this can "
        "indicate dystocia (obstructed labour) that needs intervention.",
        "Call the vet immediately — this is a clear red-flag sign",
        "Give it another few hours, since labour naturally varies in length",
    ),
    (
        "Why is a puppy nursing within the first few hours of life so critical?",
        "Colostrum carries antibody protection a newborn can only absorb efficiently in roughly the "
        "first 12-24 hours — after that window closes, much of that protection is lost.",
        "That's the window during which colostrum's antibodies can actually be absorbed well",
        "It's mainly about the puppy learning to nurse for later feeding sessions",
    ),
    (
        "What's the correct order when a puppy is found cold and hasn't nursed?",
        "Warm the puppy gradually first — a cold puppy can't digest properly, so feeding a still-cold "
        "puppy can make things worse rather than help.",
        "Warm gradually first, then reassess feeding",
        "Feed immediately to give it energy to warm itself",
    ),
    (
        "Why does the \"cold chain\" matter so much for vaccines in this context?",
        "A vaccine that wasn't kept properly cold through transport and storage may not actually work, "
        "even if administered exactly on schedule — a genuine risk given inconsistent power supply.",
        "An improperly stored vaccine may fail to protect the puppy even if given on schedule",
        "Cold storage is a manufacturer recommendation with little real-world effect",
    ),
    (
        "What's the real point of screening puppy buyers before selling to them?",
        "It's the single biggest thing a breeder can do to reduce how many puppies end up abandoned "
        "or in unsuitable homes later — not about being difficult with buyers.",
        "It meaningfully lowers the chance a puppy is later abandoned or ends up in a poor home",
        "It's mostly a way to justify charging a higher price",
    ),
    (
        "According to this course, when is the right call sometimes to NOT breed a pairing at all?",
        "The course explicitly frames \"not this time\" — because of age, health, temperament, or not "
        "being able to give a litter proper care — as good, responsible breeding judgement, not failure.",
        "Whenever age, health, temperament, or your own capacity to care for a litter says it's the right call",
        "Never — once a mating is planned, following through is always the responsible choice",
    ),
]


class Command(BaseCommand):
    help = (
        "Adds a quiz to modules 2-8 (module 1's already exists from seed_demo_course) "
        "and a final exam gating the certificate, on the Practical Dog Breeding demo course. "
        "Safe to re-run — skips anything that already exists."
    )

    def handle(self, *args, **options):
        try:
            course = Course.objects.get(slug="practical-dog-breeding")
        except Course.DoesNotExist:
            raise CommandError("Course 'practical-dog-breeding' not found — run `seed_demo_course` first.")

        org = course.organization
        created_module_quizzes = 0

        with transaction.atomic():
            # seed_demo_course originally wrote "what you just
            # watched" on module 1's quiz, back when every lesson was
            # a VIDEO placeholder — stale now that lessons are real
            # written TEXT content (fill_demo_course_content).
            Quiz.objects.filter(
                scope=Quiz.Scope.MODULE, instructions="Three quick questions on what you just watched."
            ).update(instructions="Three quick questions on what you just covered.")

            for module in course.modules.order_by("order"):
                if Quiz.objects.filter(scope=Quiz.Scope.MODULE, module=module).exists():
                    continue  # module 1 already has one from seed_demo_course
                questions = MODULE_QUESTIONS.get(module.order)
                if not questions:
                    continue

                bank = QuestionBank.objects.create(
                    organization=org,
                    name=f"Practical Dog Breeding — Module {module.order}",
                    description=f"Auto-generated check questions for module {module.order} ({module.title}).",
                )
                for stem, explanation, correct, wrong in questions:
                    q = Question.objects.create(
                        bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.MEDIUM,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)

                Quiz.objects.create(
                    scope=Quiz.Scope.MODULE, module=module,
                    title=f"Module {module.order} Check",
                    instructions="A couple of quick questions on what you just read.",
                    bank=bank, question_count=len(questions), pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                created_module_quizzes += 1

            self.stdout.write(self.style.SUCCESS(f"Created {created_module_quizzes} module quizzes."))

            if Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).exists():
                self.stdout.write(self.style.WARNING("Final exam already exists — left as-is."))
            else:
                final_bank = QuestionBank.objects.create(
                    organization=org,
                    name="Practical Dog Breeding — Final Exam",
                    description="Covers all 8 modules — must be passed to unlock the certificate.",
                )
                for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                    q = Question.objects.create(
                        bank=final_bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.MEDIUM,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)

                Quiz.objects.create(
                    scope=Quiz.Scope.FINAL, course=course,
                    title="Final Exam — Practical Dog Breeding",
                    instructions="10 questions covering everything in this course. Pass to unlock your certificate.",
                    bank=final_bank, question_count=10, pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                self.stdout.write(self.style.SUCCESS("Created the final exam."))

            if not course.requires_final_assessment:
                course.requires_final_assessment = True
                course.save(update_fields=["requires_final_assessment"])
                self.stdout.write(self.style.SUCCESS(
                    "Set requires_final_assessment=True — the certificate now only issues after passing the final exam."
                ))
            else:
                self.stdout.write(self.style.WARNING("requires_final_assessment was already True."))
