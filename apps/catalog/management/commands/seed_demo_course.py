from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, CourseFAQ, Lesson, Module, Programme, Resource
from apps.organizations.models import Organization

# Real curriculum from the breeder-track course brief, not placeholder
# copy — seeding this proves the authoring model against the content
# it actually has to hold, and gives Sam a course shell to fill in
# scripts against as he records. Video/attachment files are left
# empty; only module 1's opening lesson is marked as a sales-page
# preview.
MODULES = [
    ("Breeding with a Purpose",
     "Why you are breeding, selecting the dam and sire, conformation and "
     "temperament basics, health screening before mating, inbreeding vs "
     "line-breeding in plain language, why records matter, starting a "
     "kennel record system."),
    ("The Heat Cycle and Timing",
     "Stages of the cycle, reading the signs, why most missed matings are "
     "timing failures, what vaginal cytology and progesterone testing tell "
     "you and when to ask your vet for them, counting from the right day."),
    ("Mating and the Stud",
     "Natural mating, the tie, what to do when it fails, an honest "
     "introduction to artificial insemination, evaluating a stud before "
     "you pay for him, the popular-sire problem, stud service agreements."),
    ("Managing the Pregnancy",
     "Confirming pregnancy and when, feeding the pregnant bitch through "
     "each stage, what medicines and dewormers are safe and which are "
     "not, exercise, preparing the whelping box, the 63-day calendar."),
    ("Whelping",
     "Signs labour is starting, normal progression stage by stage, what "
     "a normal delivery looks like, what you can safely do, the red "
     "flags that mean call the vet NOW, understanding dystocia and why "
     "a caesarean is sometimes the right answer, assembling a whelping kit."),
    ("The First 21 Days",
     "Colostrum and why the first 12 hours decide everything, keeping "
     "neonates warm, weighing daily, recognising a fading puppy, "
     "hypothermia and hypoglycaemia, supplemental and tube feeding, when "
     "to intervene and when to let nature work, early socialisation."),
    ("Keeping Disease Out",
     "Parvovirus and distemper as they actually behave in Nigerian "
     "kennels, vaccination schedules and the cold chain, counterfeit "
     "product red flags, quarantine for new arrivals, ticks and "
     "tick-borne disease, Brucella canis, kennel hygiene on a real budget."),
    ("The Business of Breeding",
     "Costing a litter honestly, pricing puppies, screening buyers, "
     "deposits and contracts, safe transport, handling a buyer whose "
     "puppy falls sick, building a kennel reputation, welfare and "
     "knowing when not to breed."),
]

PLACEHOLDER_BODY = (
    "<p><em>Video not yet recorded — this lesson is a placeholder created "
    "by the seed command so the course structure exists to author "
    "against.</em></p>"
)


class Command(BaseCommand):
    help = "Seed the Practical Dog Breeding demo course with its real 8-module curriculum."

    def handle(self, *args, **options):
        with transaction.atomic():
            org, org_created = Organization.objects.get_or_create(
                slug="xpress-digital-academy",
                defaults={
                    "name": "Xpress Digital Academy",
                    "from_email": "academy@xpressdigital.ng",
                },
            )
            if org_created:
                self.stdout.write(self.style.SUCCESS(f"Created organization: {org}"))

            programme, prog_created = Programme.objects.get_or_create(
                organization=org,
                slug="dog-breeding",
                defaults={
                    "title": "Dog Breeding Courses",
                    "audience": Audience.BREEDER,
                    "description": "Courses for Nigerian dog breeders and kennel owners.",
                },
            )
            if prog_created:
                self.stdout.write(self.style.SUCCESS(f"Created programme: {programme}"))

            course, course_created = Course.objects.get_or_create(
                organization=org,
                programme=programme,
                slug="practical-dog-breeding",
                defaults={
                    "title": "Practical Dog Breeding for Nigerian Breeders",
                    "subtitle": "From choosing the right pair to selling a healthy litter — "
                                 "the judgement a good vet wishes every breeder had.",
                    "description": "<p>An 8-module course for hobby and small commercial "
                                    "breeders, built around real Nigerian conditions: "
                                    "sporadic power, distant emergency care, and the real "
                                    "prices of running a kennel.</p>",
                    "audience": Audience.BREEDER,
                    "level": Course.Level.FOUNDATION,
                    "price_ngn": 45000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": False,  # Phase 4 not built yet
                    "estimated_hours": 4.0,
                    "is_published": False,  # seed data starts unpublished on purpose
                    # Sales-page copy — drawn from the actual breeder-track
                    # course brief, not placeholder text.
                    "sales_headline": "Stop losing litters to things you could have caught early",
                    "sales_subheadline": "8 modules on breeding with judgement — from choosing the "
                                          "pair to knowing exactly when to call your vet.",
                    "target_audience": (
                        "Hobby and small commercial breeders with 1–10 breeding females\n"
                        "Breeders of German Shepherd, Rottweiler, Caucasian Shepherd, Boerboel, "
                        "Belgian Malinois, Lhasa Apso, and local crosses\n"
                        "Anyone who has lost a litter and never found out why\n"
                        "Breeders who want to be a better partner to their vet, not a replacement for one"
                    ),
                    "not_for": (
                        "Anyone looking to learn surgery, prescribing, or lab interpretation — "
                        "that's a vet's job, and this course teaches you to recognise the moment "
                        "you need one\n"
                        "Veterinarians — see the separate Canine Reproduction for Practitioners track"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "A practical, Nigeria-specific dog breeding course — "
                                         "real prices, real constraints, and exactly when to call your vet.",
                },
            )
            if not course_created:
                self.stdout.write(
                    self.style.WARNING(f"Course already exists: {course} — leaving modules/lessons as-is.")
                )
                return

            self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))

            module_1 = None
            for i, (title, summary) in enumerate(MODULES, start=1):
                module = Module.objects.create(
                    course=course,
                    order=i,
                    title=title,
                    summary=summary,
                    unlock_rule=Module.UnlockRule.SEQUENTIAL,
                )
                if i == 1:
                    module_1 = module
                Lesson.objects.create(
                    module=module,
                    order=1,
                    title=f"Module {i}: {title}",
                    type=Lesson.Type.VIDEO,
                    body=PLACEHOLDER_BODY,
                    duration_seconds=1500,  # 25 min placeholder
                    is_preview=(i == 1),
                )

            self.stdout.write(self.style.SUCCESS(f"Created {len(MODULES)} modules with 1 lesson each."))

            resource = Resource(
                course=course,
                title="63-Day Whelping Calendar (placeholder)",
                description="Content pending — real downloadable to be produced during "
                             "module 4 recording.",
                download_count=0,
            )
            resource.file.save(
                "whelping-calendar-placeholder.txt",
                ContentFile(
                    b"Placeholder for the 63-day whelping calendar.\n"
                    b"Replace this file in admin once the real one-pager is designed "
                    b"(see the module 4 course-content brief for the layout)."
                ),
                save=True,
            )
            bank = QuestionBank.objects.create(
                organization=org,
                name="Practical Dog Breeding — Module 1",
                description="Sample questions demonstrating the assessment app against real "
                             "course structure. Not the real 10-question bank the course-content "
                             "brief calls for per module — replace via CSV import in admin.",
            )
            for stem, explanation, correct, wrong in [
                (
                    "A breeder tells you she always mates her bitch on the first sign of "
                    "standing heat, “because that's when she's ready.” What's the problem with this?",
                    "Standing heat can start days before ovulation actually happens — mating "
                    "on the first sign alone is exactly the kind of timing failure that "
                    "produces bitches wrongly labelled “infertile.” Progesterone testing or "
                    "vaginal cytology, not the first visible sign, is what actually confirms "
                    "the fertile window.",
                    "It risks missing the actual fertile window — signs of heat and ovulation don't happen on the same day",
                    "There's no problem — standing heat is the only sign that matters",
                ),
                (
                    "A litter is due in 3 days by the breeder's count, but she's not sure "
                    "which day she started counting from. What should she do?",
                    "The 63-day calendar is only as good as the day it's counted from. When "
                    "the start date is uncertain, the right move is to confirm with her vet "
                    "(ultrasound staging or a recount from the actual mating date) rather than "
                    "trust an approximate calendar this close to whelping.",
                    "Confirm the actual mating date and due window with her vet rather than guess",
                    "Round down and prepare for whelping today, just in case",
                ),
                (
                    "A 2-day-old puppy is cold to the touch and won't nurse, but the rest of "
                    "the litter is fine. What is the single most urgent first action?",
                    "Hypothermia in a neonate shuts down the ability to digest — feeding a "
                    "cold puppy before warming it (slowly, not with direct high heat) can "
                    "cause more harm. Warming first, then reassessing, is the sequence that "
                    "actually gives the puppy a chance; calling the vet matters too but comes "
                    "right after, not instead of, starting to warm the puppy.",
                    "Warm the puppy gradually before attempting to feed it",
                    "Force-feed it immediately so it doesn't lose more strength",
                ),
            ]:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)

            Quiz.objects.create(
                scope=Quiz.Scope.MODULE,
                module=module_1,
                title="Module 1 Check",
                instructions="Three quick questions on what you just covered.",
                bank=bank,
                question_count=3,
                pass_mark=70,
                max_attempts=0,
                time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created a sample question bank and module 1 quiz."))

            faqs = [
                ("Do I need to be a vet to take this course?",
                 "No — it's built for breeders, not vets. Any clinical decision routes you to your "
                 "own vet; the course teaches you to recognise that moment early, which is the real skill."),
                ("How long do I have access?",
                 "Lifetime access — go at your own pace, and revisit any module whenever you need it."),
                ("Is there a certificate?",
                 "Yes, a Certificate of Completion once you finish every module."),
            ]
            for order, (question, answer) in enumerate(faqs, start=1):
                CourseFAQ.objects.create(course=course, question=question, answer=answer, order=order)
            self.stdout.write(self.style.SUCCESS(f"Created {len(faqs)} FAQ entries."))

            self.stdout.write(self.style.SUCCESS("Done. Course is unpublished — review in admin before flipping is_published."))
