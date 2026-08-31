from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Second of the ~30-topic Vet-blog cross-promotion batch (see
# seed_newcastle_disease_course.py's header for the full context).
# Content maps near 1:1 onto the Vet session's already-modular blog
# article, per their own note when relaying it. Sits in the EXISTING
# "Dog Breeding Courses" programme (BREEDER audience) alongside the
# tiered Practical Dog Breeding track — deliberately positioned as a
# genetics/compliance-focused companion course, not a replacement for
# that track's broader day-to-day breeding content.

MODULES = [
    ("Genetics and Hereditary Disease Screening",
     """<h2>Screen before you breed, not after a problem appears</h2>
<p>Breed-specific screening — hip/elbow dysplasia (OFA/PennHIP), eye disorders (CERF/OFA), cardiac disease, and breed-specific DNA panels (degenerative myelopathy, von Willebrand disease, progressive retinal atrophy, among others relevant to the breed) — belongs before a pairing is chosen, not after a litter is already on the ground and a problem shows up.</p>
<h2>Pedigree research</h2>
<p>Look 3-4 generations back for recurring hereditary conditions. Avoid close linebreeding on a known carrier line without genetic counseling — "the parents both look fine" is not the same as "the line is clear."</p>
<h2>Coefficient of inbreeding (COI)</h2>
<p>Keep it low. Breed-club databases can calculate COI from a proposed pairing before you commit to it — a five-minute check that can prevent a genuinely difficult conversation with a puppy buyer later.</p>"""),
    ("Pre-Breeding Health and Fertility Workup",
     """<h2>Full veterinary exam of both sire and dam</h2>
<p>Including a brucellosis test — frequently overlooked outside professional kennels, and one of the more consequential things to skip given how it can affect an entire breeding operation, not just one dog.</p>
<h2>Vaccination and parasite status</h2>
<p>Confirm both are current before pregnancy begins, not mid-pregnancy when options for correcting a gap narrow.</p>
<h2>Progesterone timing</h2>
<p>Timing a breeding by progesterone testing, not by counting days from the first sign of heat, is what actually maximizes the odds of conception on the first attempt — worth the extra step and cost relative to a failed breeding cycle.</p>"""),
    ("Pregnancy, Nutrition, and Whelping Preparation",
     """<h2>Nutrition through gestation</h2>
<p>Nutritional needs rise only modestly through the first two-thirds of gestation, then substantially in the final third. Transition the diet gradually across this curve — don't wait until after whelping to make the change.</p>
<h2>Confirming litter size before you need to know it</h2>
<p>Radiography around day 55-58 gives a reliable fetal count. This isn't just curiosity — knowing the expected count is what tells you, in real time during labor, whether whelping has genuinely stalled and needs veterinary help, versus is simply between puppies normally.</p>
<h2>Preparing the whelping area</h2>
<p>Clean, warm, low-traffic, and a box the dam has already settled into well before labor begins — not introduced for the first time as contractions start.</p>"""),
    ("Whelping and the First 72 Hours",
     """<h2>Normal labor versus a real emergency</h2>
<p>Straining for 30-60+ minutes without producing a puppy, a gap of 2+ hours between puppies when more are expected, or any visible fetal distress are all signals that this has moved from "normal labor" to "needs veterinary intervention now" — not signs to wait out.</p>
<h2>Neonatal care in the first hours</h2>
<p>Clear airways, stimulate breathing, tie and disinfect the umbilical cord, and ensure colostrum intake within the first hours of life — colostrum is the puppy's only real source of passive immunity, and the window for it closes fast.</p>
<h2>The single most reliable early warning sign</h2>
<p>Daily weight tracking for the first two weeks. Failure to gain weight is the earliest reliable indicator that something is wrong, often well before any other visible sign appears.</p>"""),
    ("Socialization and Early Development",
     """<h2>The critical socialization window</h2>
<p>Roughly 3-14 weeks of age is when structured, varied, low-stress exposure measurably shapes adult temperament. This window is not optional extra credit — it's a real developmental period with lasting effects.</p>
<h2>Early neurological stimulation</h2>
<p>A set of brief, mild stress exercises applied in the first days of life, used by many professional breeding programs as part of early development work.</p>
<h2>Why 8 weeks, not earlier</h2>
<p>Puppies shouldn't go to new homes before 8 weeks of age. Time spent with the dam and littermates through that window genuinely shapes bite inhibition and social skills — sending a puppy home earlier trades a short-term convenience for a real, lasting cost to that dog's development.</p>"""),
    ("Record-Keeping, Ethics, and Regulatory Compliance",
     """<h2>Health records that are actually given, not just claimed</h2>
<p>Complete, transferable health records for every puppy — handed over in writing, not asserted verbally at pickup.</p>
<h2>A health guarantee that reflects what was actually screened</h2>
<p>A written guarantee should map directly onto the screening actually done in Module 1 — not a generic template that overstates what was checked.</p>
<h2>Registration and compliance</h2>
<p>Registration with the relevant breed club or kennel association, and — particularly for cross-state sales in Nigeria — working with a licensed veterinarian for health certification.</p>
<h2>What actually separates a responsible program</h2>
<p>A genuine willingness to take a dog back at any point in its life, for any reason, separates a responsible breeding program from an accidental or purely commercial one more reliably than almost any other single practice on this list.</p>
<h2>The bottom line</h2>
<p>None of this is exotic. It's standard veterinary and canine-genetics knowledge. What separates a responsible program from an accidental one is doing all of it, consistently, and being able to document it.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is a brucellosis test on both sire and dam significant, beyond being one more pre-breeding item to check?",
        "It's frequently overlooked outside professional kennels, yet a positive result has real implications for an "
        "entire breeding operation — not just the two dogs directly involved.",
        "It's often skipped but has consequences reaching well beyond the two individual dogs tested",
        "It only ever affects the two dogs being bred and has no wider relevance to a breeding program",
    ),
    (
        "Why does timing a breeding by progesterone testing beat counting days from the first sign of heat?",
        "Progesterone timing tracks the dog's actual hormonal cycle rather than an external sign that can vary "
        "significantly between individuals, which is what actually maximizes first-attempt conception odds.",
        "It tracks the individual dog's real hormonal timing rather than a general day-count estimate",
        "Day-counting from the first sign of heat is always exactly as reliable as progesterone testing",
    ),
    (
        "Why does confirming an expected fetal count (e.g. via a day 55-58 radiograph) matter during labor itself?",
        "Knowing the expected count is what lets a breeder recognize in real time whether whelping has genuinely "
        "stalled and needs veterinary help, rather than simply being a normal pause between puppies.",
        "It gives a real-time reference for recognizing a genuine stall in labor versus a normal pause",
        "The fetal count has no practical use once labor has actually begun",
    ),
    (
        "What is the earliest reliable sign that a neonatal puppy has a problem in its first two weeks?",
        "Failure to gain weight on daily tracking is typically the earliest reliable indicator of a problem, often "
        "showing up before any other visible sign.",
        "Failure to gain weight on daily tracking, often before any other sign becomes visible",
        "Puppies show no measurable warning signs before a crisis becomes visibly obvious",
    ),
    (
        "Why shouldn't puppies go to new homes before 8 weeks of age?",
        "Time with the dam and littermates through that window genuinely shapes bite inhibition and social skills — "
        "sending a puppy home earlier trades a short-term convenience for a real, lasting developmental cost.",
        "That time with the dam and littermates has a real, lasting effect on bite inhibition and social development",
        "The exact age a puppy leaves has no real bearing on its later temperament or behavior",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'The Responsible Dog Breeder's Curriculum' — a genetics-and-compliance-focused "
        "companion course to the existing tiered Practical Dog Breeding track, matching a Vet "
        "Marketplace blog post, second of the ~30-topic cross-promotion batch. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme = Programme.objects.filter(organization=org, slug="dog-breeding").first()
        if not programme:
            self.stderr.write(self.style.ERROR(
                "Run seed_demo_course first — no 'Dog Breeding Courses' programme found."
            ))
            return

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="responsible-dog-breeders-curriculum",
                defaults={
                    "title": "The Responsible Dog Breeder's Curriculum",
                    "subtitle": "What every serious breeder must master — genetics, veterinary screening, and "
                                 "compliance, taken as a discipline rather than left to chance.",
                    "description": "<p>A 6-module course covering the full arc of responsible breeding: hereditary "
                                    "disease screening and pedigree research, pre-breeding health and fertility "
                                    "workups, pregnancy and whelping preparation, the critical first 72 hours, "
                                    "socialization and early development, and honest record-keeping and regulatory "
                                    "compliance.</p>",
                    "audience": Audience.BREEDER,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 6000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 2.5,
                    "is_published": False,
                    "sales_headline": "Breeding well is a discipline, not luck — here's what it actually requires",
                    "sales_subheadline": "6 modules on genetics screening, health workups, whelping, early "
                                          "development, and the compliance that separates a real program from an "
                                          "accidental one.",
                    "target_audience": (
                        "Hobby and small commercial breeders wanting a structured, genetics-and-compliance-first "
                        "approach\n"
                        "Breeders already through the Practical Dog Breeding track wanting a deeper, more "
                        "disciplined framework\n"
                        "Anyone deciding whether to breed a first litter responsibly"
                    ),
                    "not_for": (
                        "Complete beginners wanting day-to-day breeding basics first — see Practical Dog Breeding "
                        "for Nigerian Breeders instead"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Responsible dog breeding CE — genetics screening, health workups, "
                                         "whelping, and compliance, as a real discipline.",
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
                organization=org, name="The Responsible Dog Breeder's Curriculum — Final Exam",
                description="Covers all 6 modules — must be passed to unlock the certificate.",
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
                title="Final Exam — The Responsible Dog Breeder's Curriculum",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
