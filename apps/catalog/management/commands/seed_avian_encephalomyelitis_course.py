from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Eleventh of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A nervous-system virus with an unusual epidemiological signature</h2>
<p>Avian encephalomyelitis is caused by avian encephalomyelitis virus (AEV), a picornavirus that primarily affects the nervous system of young chicks. What makes this disease distinctive isn't the virus itself so much as when and how outbreaks actually happen.</p>
<h2>Why a breeder flock's FIRST exposure is the whole story</h2>
<p>The classically significant transmission route is vertical — a newly-infected breeder hen passes the virus through the egg to her chicks, producing an outbreak tied to that specific hatch window. Breeder hens shed the virus only transiently before becoming immune, which means the vulnerable period is specifically the weeks around a breeder flock's FIRST exposure to AEV — not an ongoing risk throughout that flock's productive life. Horizontal, fecal-oral spread also occurs independently of this vertical route. Affected chicks are typically one to three weeks old.</p>"""),
    ("Clinical Findings",
     """<h2>The hallmark sign</h2>
<p>Progressive ataxia — incoordination, sitting on the hocks — appears first, along with a fine head and neck tremor that's especially noticeable on handling or under stress. This tremor is the hallmark sign of avian encephalomyelitis and is genuinely distinctive once you know to look for it. Disease progresses to paralysis and an inability to stand or eat.</p>
<h2>What the breeder hen herself shows — often nothing obvious</h2>
<p>Breeder hens may show only a transient egg production drop at the time of their first exposure, with disease then appearing in their chicks weeks later. This time gap between the breeder's mild, easily-missed signs and the chicks' obvious neurological disease is exactly why understanding the vertical transmission pattern from the previous module matters so much for tracing an outbreak back to its source.</p>"""),
    ("Diagnosis",
     """<h2>Often distinctive on its own</h2>
<p>The characteristic tremor and ataxia in young chicks from a specific hatch is often distinctive enough to build a strong clinical suspicion on its own, particularly when it clusters around one hatch window rather than appearing evenly across ages.</p>
<h2>Confirming and predicting risk</h2>
<p>Histopathology confirms the diagnosis, showing CNS lesions — neuronal degeneration and lymphocytic infiltration; gross lesions are otherwise nonspecific. Breeder serology, tracking rising titers, can actually predict which upcoming hatches are at risk, giving a real window to act before chicks show disease.</p>
<h2>Key differentials</h2>
<p>The neural form of Marek's disease, nutritional or toxic causes of neurological signs, and the neurological form of Newcastle disease all need to be considered.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>No treatment, and a real welfare decision</h2>
<p>There is no treatment — supportive care for mild cases, and culling severely affected chicks on welfare grounds once paralysis sets in.</p>
<h2>Why the breeder flock resolves itself, but timing still matters</h2>
<p>A breeder flock becomes immune within weeks of its first exposure, which naturally protects subsequent chicks through maternal antibody from that point forward — the outbreak is, in a real sense, self-limiting at the breeder level. But that natural process still allows one bad window of affected hatches before immunity develops.</p>
<h2>Prevention — the critical timing point</h2>
<p>Vaccinating breeder pullets BEFORE lay is standard prevention, and the timing here is genuinely critical: it avoids the mid-lay first-exposure scenario that otherwise produces a wave of affected chicks from an already-laying, previously unexposed flock.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is a breeder flock's FIRST exposure to AEV the critical epidemiological event, rather than ongoing circulation?",
        "Breeder hens shed the virus only transiently before becoming immune, so the vulnerable window is "
        "specifically the weeks around that first exposure — not a sustained ongoing risk afterward.",
        "Breeder hens shed only transiently before becoming immune, making the first-exposure window the real risk period",
        "AEV circulates continuously in an infected breeder flock for the rest of its productive life",
    ),
    (
        "What is the hallmark clinical sign of avian encephalomyelitis in young chicks?",
        "A fine head and neck tremor, especially noticeable on handling or under stress, alongside progressive "
        "ataxia — genuinely distinctive once recognized.",
        "A fine head and neck tremor, especially noticeable on handling or under stress",
        "Sudden death with no preceding clinical signs of any kind",
    ),
    (
        "Why can breeder serology (tracking rising titers) be more useful than waiting for chicks to show disease?",
        "It can predict which upcoming hatches are at risk before chicks actually show neurological signs, giving "
        "a real window to act ahead of an outbreak rather than only reacting to one.",
        "It can flag at-risk upcoming hatches before affected chicks actually show clinical disease",
        "Breeder serology has no predictive value and only confirms disease after chicks are already affected",
    ),
    (
        "Why is vaccinating breeder pullets BEFORE lay specifically important, rather than at any convenient point?",
        "It avoids the mid-lay first-exposure scenario, where an already-laying, previously unexposed flock's "
        "first natural exposure would otherwise produce a wave of affected chicks.",
        "It avoids a mid-lay first-exposure scenario that would otherwise produce a wave of affected chicks",
        "Vaccination timing has no real bearing on outcomes as long as it happens at some point before exposure",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Avian Encephalomyelitis' — eleventh of the poultry-only ~20-topic "
        "Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="avian-encephalomyelitis",
                defaults={
                    "title": "Avian Encephalomyelitis",
                    "subtitle": "A nervous-system disease striking young chicks specifically from breeder flocks "
                                 "recently exposed for the first time.",
                    "description": "<p>A 4-module continuing-education course on avian encephalomyelitis — "
                                    "etiology and the first-exposure epidemiological pattern that defines "
                                    "outbreaks, the hallmark tremor and ataxia in young chicks, diagnosis "
                                    "including breeder serology as a predictive tool, and treatment/control/"
                                    "prevention centered on breeder-pullet vaccination timing.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "A tremor that's hard to miss once you know to look for it",
                    "sales_subheadline": "4 modules on avian encephalomyelitis — the first-exposure pattern, "
                                          "diagnosis, and why breeder-pullet timing prevents a wave of sick chicks.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners investigating a hatch-specific neurological outbreak in young chicks\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Avian encephalomyelitis CE for vets — first-exposure pattern, hallmark "
                                         "tremor, and breeder-pullet vaccination timing.",
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
                organization=org, name="Avian Encephalomyelitis — Final Exam",
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
                title="Final Exam — Avian Encephalomyelitis",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
