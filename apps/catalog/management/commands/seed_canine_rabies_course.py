from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourth of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>What causes it, and why it matters this much</h2>
<p>Rabies is caused by rabies virus, a lyssavirus, transmitted via bite or saliva contact. It's fatal and essentially untreatable once signs appear — exactly why prevention and knowing the exposure protocol matter more here than almost anything else covered on this platform.</p>
<h2>A dog-mediated public health priority</h2>
<p>Dogs remain a major rabies vector in many parts of the world, including Nigeria — dog-mediated rabies is specifically a human public health priority, since the overwhelming majority of human rabies deaths worldwide trace back to dog bites. This isn't only an animal health issue; it's one of the clearest points where veterinary practice directly protects human life.</p>"""),
    ("Clinical Findings",
     """<h2>Highly variable incubation</h2>
<p>Incubation is highly variable — weeks to months — and shorter with bites to the head or face, given the shorter distance the virus has to travel to reach the central nervous system.</p>
<h2>Two forms, both fatal</h2>
<p>The "furious" form presents with aggression, disorientation, hypersalivation, and difficulty swallowing — the presentation most people picture when they think of rabies. The "dumb," or paralytic, form presents very differently: progressive paralysis and quiet withdrawal, which is easily mistaken for something else entirely. This is a real recognition risk worth taking seriously — a quiet, withdrawn, paralyzed dog doesn't fit the popular image of rabies, but is just as infected and just as fatal.</p>"""),
    ("Diagnosis",
     """<h2>Why there's no live-animal test</h2>
<p>There is no reliable live-animal test for rabies — confirmation is only possible via brain tissue examination after death. This single fact is exactly why the practical response to a bite is based on exposure history and a defined observation period, not on a diagnostic test performed in the moment.</p>"""),
    ("Prevention and the After-a-Bite Protocol",
     """<h2>Prevention is the entire strategy</h2>
<p>Vaccination is genuinely effective and is LEGALLY REQUIRED in Nigeria and most jurisdictions — not discretionary. Given the previous module's diagnostic limitation, prevention isn't just the best strategy, it's essentially the only strategy that matters once exposure risk exists.</p>
<h2>What actually happens after a bite</h2>
<p>A dog bitten by a wild or unknown animal needs immediate veterinary assessment. A dog that bites a person is typically legally required to be CONFINED AND OBSERVED for a defined period — commonly around 10 days in many jurisdictions — rather than immediately euthanized for testing. This protocol exists because a dog shedding virus at the time of the bite will reliably show signs within that observation window if it's actually infected. This protects both the person (informing their post-exposure treatment decision) and the dog (avoiding unnecessary euthanasia of a genuinely healthy animal).</p>
<h2>Human exposure always needs its own response</h2>
<p>Any person bitten by a dog of unknown vaccination status should seek medical attention promptly, regardless of how healthy the dog appears — the dog's apparent health at the moment of the bite says nothing reliable about its actual infection status, given the variable incubation period covered earlier.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's or public health authority's own guidance on a specific exposure incident. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is the 'dumb' (paralytic) form of rabies described as a real recognition risk?",
        "It presents as quiet withdrawal and progressive paralysis rather than the aggression most people expect "
        "from rabies, making it easy to mistake for a different, less alarming condition.",
        "It presents as quiet withdrawal and paralysis, easily mistaken for something other than rabies",
        "The dumb form is actually more visually dramatic and easier to recognize than the furious form",
    ),
    (
        "Why is rabies confirmation only possible via brain tissue examination after death, and how does that shape the practical response to a bite?",
        "There's no reliable live-animal test, so the practical response is built on exposure history and a "
        "defined observation period rather than waiting for a diagnostic test result that simply isn't available.",
        "With no live-animal test available, response is based on exposure history and a defined observation period",
        "A reliable live-animal blood test exists but is rarely used due to cost in most veterinary practices",
    ),
    (
        "Why is a biting dog typically confined and observed for a defined period rather than immediately euthanized for testing?",
        "A dog shedding virus at bite-time will reliably show signs within that observation window if infected — "
        "the protocol protects both the person's treatment decision and a genuinely healthy dog from unnecessary euthanasia.",
        "A dog infectious at the time of the bite will reliably develop signs within that defined window",
        "Confinement and observation exist purely as a formality with no real diagnostic value",
    ),
    (
        "Why should a person bitten by a dog of unknown vaccination status seek medical attention promptly, regardless of how healthy the dog looks?",
        "Incubation is highly variable, so a dog's apparent health at the moment of the bite says nothing reliable "
        "about whether it was actually infectious at that time.",
        "The dog's apparent health at the time of the bite doesn't reliably reflect its true infection status",
        "A dog that appears completely healthy at the time of a bite can be assumed to be rabies-free",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Canine Rabies: Prevention, Exposure Protocol, and the Law' — fourth "
        "of the mixed dogs/cats/livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="canine-rabies-prevention-exposure-protocol",
                defaults={
                    "title": "Canine Rabies: Prevention, Exposure Protocol, and the Law",
                    "subtitle": "Fatal and essentially untreatable once signs appear — exactly why prevention and "
                                 "knowing the exposure protocol matter more here than almost anything else.",
                    "description": "<p>A 4-module continuing-education course on canine rabies — etiology and why "
                                    "dog-mediated rabies is a human public health priority in Nigeria, clinical "
                                    "findings including the easily-missed paralytic form, why no live-animal test "
                                    "exists, and the legally required vaccination and bite-response protocol.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "No live-animal test exists — know the protocol before you need it",
                    "sales_subheadline": "4 modules on canine rabies — the easily-missed paralytic form, why "
                                          "diagnosis relies on protocol not testing, and the legal bite-response process.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners handling a real bite incident and needing to know the legal protocol\n"
                        "Anyone advising clients on rabies vaccination requirements in Nigeria"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Canine rabies CE for vets — the paralytic form, diagnosis limits, and the "
                                         "legal vaccination and bite-response protocol.",
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
                organization=org, name="Canine Rabies — Final Exam",
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
                title="Final Exam — Canine Rabies",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
