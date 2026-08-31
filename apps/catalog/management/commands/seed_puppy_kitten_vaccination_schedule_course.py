from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourth of the new "Pet Owner Education" track (see
# seed_recognizing_vet_emergency_course.py's header for the
# categorization rationale and Programme details).

MODULES = [
    ("Why the Series Exists, Not Just One Shot",
     """<h2>Maternal antibody's unpredictable timeline</h2>
<p>Maternal antibody fades at an unpredictable rate in each individual animal, and can actually NEUTRALIZE a vaccine if it's given too early. A single "normal age" shot doesn't reliably protect every individual puppy or kitten — the SERIES exists specifically to catch each animal at whatever point its own maternal antibody has actually dropped enough for the vaccine to take effect, since nobody can know that exact point in advance for an individual animal.</p>
<h2>A puppy or kitten with one shot is genuinely not protected yet</h2>
<p>This is the single most important idea in this course: an animal that's had only the first shot in the series is genuinely not reliably protected, no matter how the timing looks on a calendar. The series isn't extra caution layered on top of protection that already exists after dose one — it's what actually builds that protection in the first place.</p>"""),
    ("Typical Puppy and Kitten Schedules",
     """<h2>Puppies</h2>
<p>The first combination vaccine (covering distemper, parvovirus, and others) typically starts around 6-8 weeks of age. Boosters follow every 3-4 weeks until AT LEAST 16 weeks — that 16-week endpoint matters specifically because it's the point where maternal antibody has reliably waned in nearly all puppies, not an arbitrary round number. Rabies vaccination follows local legal requirements.</p>
<h2>Kittens</h2>
<p>The same general shape applies: a first combination vaccine (covering panleukopenia and the main upper respiratory viruses) around 6-8 weeks, with boosters every 3-4 weeks until at least 16 weeks, and rabies per local requirements. The exact products and timing can vary by vet, brand, and local disease risk — this is a typical shape, not a universal fixed rule.</p>"""),
    ("Why 'Just One Shot' Isn't Enough, and After the Series",
     """<h2>The real, specific danger of an interrupted series</h2>
<p>An animal given only the first shot, then exposed to disease before the later doses, is genuinely NOT reliably protected — a vaccinated-LOOKING animal can still develop full-blown disease if the series was interrupted partway through. This exact gap is why parvovirus and panleukopenia remain consistent threats specifically in the 6-16 week window, already covered in their own courses on this platform — the danger isn't abstract, it's this specific timing gap.</p>
<h2>What happens after the initial series</h2>
<p>Adult booster schedules vary from annual to longer intervals, and this is genuinely a conversation to have with a vet rather than a one-size-fits-all rule — worth revisiting as an animal's lifestyle changes, not decided once and forgotten.</p>
<h2>A note on this course's limits</h2>
<p>This is general educational content for pet owners, not a substitute for your vet's specific vaccination plan for your animal, which should account for local disease risk and the individual animal's health.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does the vaccination series exist instead of a single shot given at one standard age?",
        "Maternal antibody fades at an unpredictable rate per individual animal, so the series is what catches "
        "each animal at whatever point its own antibody has dropped enough for the vaccine to actually work.",
        "Maternal antibody fades unpredictably per animal, so the series catches each one at its own right moment",
        "The series exists purely as an extra safety margin on top of protection dose one already fully provides",
    ),
    (
        "Why is a puppy or kitten with only the first shot in its series considered genuinely unprotected, not just 'partially covered'?",
        "The series is what actually builds protection in the first place — it isn't extra caution layered onto "
        "protection dose one already provides, so an interrupted series leaves real, meaningful vulnerability.",
        "The series is what actually builds the protection, so dose one alone doesn't yet provide reliable coverage",
        "The first dose alone typically provides close to full protection, with later doses adding only marginal benefit",
    ),
    (
        "Why does the roughly 16-week completion point matter specifically, rather than being an arbitrary round number?",
        "It's the point where maternal antibody has reliably waned in nearly all puppies and kittens, making it a "
        "genuine biological threshold rather than a convenient scheduling choice.",
        "It's the point where maternal antibody has reliably waned in nearly all puppies and kittens by then",
        "The 16-week mark is a purely administrative convention with no real connection to maternal antibody levels",
    ),
    (
        "Why does the 6-16 week window specifically remain a consistent threat window for diseases like parvovirus and panleukopenia?",
        "It's exactly the period when a puppy or kitten with an incomplete vaccination series can look "
        "vaccinated while still lacking reliable protection, creating a real, specific gap rather than a vague general risk.",
        "It's the exact window where an incomplete series can leave an animal looking protected while it still isn't",
        "This window carries no special significance beyond being roughly when most vaccination series happen to start",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Vaccination Schedules for Puppies and Kittens: A Practical "
        "Timeline' — fourth course in the 'Pet Owner Education' track. Safe to re-run."
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
            },
        )
        if prog_created:
            self.stdout.write(self.style.SUCCESS(f"Created programme: {programme}"))

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="vaccination-schedules-puppies-kittens",
                defaults={
                    "title": "Vaccination Schedules for Puppies and Kittens: A Practical Timeline",
                    "subtitle": "A puppy or kitten with just one shot is genuinely not protected yet — the full "
                                 "series exists because nobody can predict exactly when maternal antibody stops "
                                 "interfering with the vaccine.",
                    "description": "<p>A 3-module guide for pet owners on puppy and kitten vaccination — why the "
                                    "full series matters more than any single shot, typical puppy and kitten "
                                    "schedules, and why an interrupted series leaves real, meaningful risk.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_published": False,
                    "sales_headline": "One shot doesn't mean protected yet — know why the full series matters",
                    "sales_subheadline": "A free, practical timeline for puppy and kitten vaccination — and why "
                                          "an interrupted series is a real, specific risk.",
                    "target_audience": (
                        "Any new puppy or kitten owner\n"
                        "Anyone unsure why their vet keeps scheduling more shots after the first one\n"
                        "Breeders wanting a clear reference to share with new owners"
                    ),
                    "not_for": "",
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Free guide for pet owners — puppy and kitten vaccination timeline and "
                                         "why the full series matters.",
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
                organization=org, name="Vaccination Schedules for Puppies and Kittens — Final Check",
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
                title="Final Check — Vaccination Schedules for Puppies and Kittens",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full guide. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final check."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
