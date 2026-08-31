from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Nineteenth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Written
# alongside seed_broiler_ascites_course.py — shares the same
# underlying growth-versus-cardiovascular-capacity root cause, but
# this course repeatedly contrasts against ascites's different
# mechanism, presentation, and necropsy picture, matching how the two
# source articles were framed together.

MODULES = [
    ("A Different Mechanism from Ascites",
     """<h2>Same underlying pressure, different failure mode</h2>
<p>Sudden death syndrome (SDS) reflects the same cardiovascular system struggling with rapid growth already covered in the Ascites Syndrome course — but through a genuinely different mechanism. SDS is believed to be a fatal cardiac arrhythmia, possibly linked to electrolyte or metabolic imbalance during peak metabolic activity, versus ascites's chronic heart-failure-and-fluid pattern building up over time.</p>
<h2>Who's affected, and when</h2>
<p>Fast-growing broilers, typically in the second half of the growing period at their heaviest weight and highest metabolic demand, are affected. The best-performing, heaviest birds are disproportionately affected — the same counterintuitive pattern already established for ascites. Some reported patterns show males affected more, consistent with their generally faster growth rate.</p>"""),
    ("Clinical Findings and Lesions — Notably Unremarkable",
     """<h2>Almost no warning, unlike nearly everything else</h2>
<p>Essentially NO clinical signs precede death in most cases — this genuinely distinguishes SDS from almost every other condition covered on this platform. Birds are simply found dead, often on their backs, with occasional brief wing-flapping witnessed at the actual moment of death.</p>
<h2>An unremarkable necropsy is itself a diagnostic clue</h2>
<p>Necropsy findings are notably UNREMARKABLE — and that absence of findings is itself diagnostically useful, in sharp contrast to ascites's clear right-heart enlargement and fluid accumulation. Mild lung congestion is possible; the heart shows minor changes at most, nothing resembling the right ventricular hypertrophy seen in ascites. The crop and gizzard are often full, indicating death shortly after normal feeding, not during a period of illness.</p>"""),
    ("Diagnosis and Prevention",
     """<h2>A presumptive diagnosis by pattern and exclusion</h2>
<p>Diagnosis is presumptive: the classic picture — a healthy, fast-growing, well-fed broiler found dead, often on its back, with an unremarkable necropsy — combined with ruling out other causes. There is no single confirmatory test, which makes recognizing this pattern, rather than searching for a positive finding, the practical diagnostic approach.</p>
<h2>No treatment — death is typically instantaneous</h2>
<p>There is no individual treatment; death is typically instantaneous. Prevention overlaps substantially with ascites prevention — feeding programs that moderate the earliest and peak growth rate — but SDS also has some genuinely distinct prevention angles. Avoiding sudden loud noises or disturbances, especially around feeding, is linked to triggering the fatal arrhythmias believed to cause SDS — a distinct angle from anything relevant to ascites. Lighting programs that include a REAL dark or rest period, rather than 24-hour light, are associated with reduced incidence. Genetics also play a role, as with ascites.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for a specific operation. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "How does sudden death syndrome's mechanism differ from ascites syndrome's, despite sharing the same underlying pressure?",
        "SDS is believed to be a fatal cardiac arrhythmia during peak metabolic activity, while ascites is a "
        "chronic heart-failure-and-fluid-accumulation pattern that builds up over time.",
        "SDS involves a sudden fatal arrhythmia, while ascites involves chronic heart failure and fluid buildup",
        "SDS and ascites are actually caused by entirely unrelated mechanisms with no shared underlying cause",
    ),
    (
        "Why does an unremarkable necropsy actually count as a useful diagnostic finding in a suspected SDS case?",
        "The absence of the fluid accumulation and right heart enlargement seen in ascites — combined with the "
        "classic history — helps distinguish SDS from that and other conditions, even without a positive finding.",
        "The absence of ascites-like findings, combined with the classic history, helps distinguish SDS by exclusion",
        "An unremarkable necropsy provides no useful diagnostic information in any suspected SDS case",
    ),
    (
        "Why is avoiding sudden loud noises or disturbances around feeding time relevant to SDS prevention specifically?",
        "It's linked to triggering the fatal cardiac arrhythmias believed to cause SDS — a distinct prevention "
        "angle that isn't part of the ascites-prevention overlap.",
        "It's linked to triggering the fatal arrhythmias believed to underlie SDS, a distinct angle from ascites prevention",
        "Noise and disturbance have no documented connection to SDS risk and are unrelated to prevention",
    ),
    (
        "Why is SDS diagnosis described as presumptive rather than based on a single confirmatory test?",
        "There is no single confirmatory test — diagnosis relies on recognizing the classic pattern (healthy, "
        "fast-growing bird found dead, unremarkable necropsy) and ruling out other causes.",
        "There's no single confirmatory test, so diagnosis relies on pattern recognition and ruling out alternatives",
        "A definitive blood test exists for SDS but is rarely used due to cost in most practice settings",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Sudden Death Syndrome of Broiler Chickens' — nineteenth of the "
        "poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="broiler-sudden-death-syndrome",
                defaults={
                    "title": "Sudden Death Syndrome of Broiler Chickens",
                    "subtitle": "A healthy-looking broiler, found dead, often flipped onto its back — with almost "
                                 "no warning sign beforehand. Unlike nearly everything else, that's the point.",
                    "description": "<p>A 3-module continuing-education course on broiler sudden death syndrome — "
                                    "how its cardiac-arrhythmia mechanism differs from ascites's chronic "
                                    "heart-failure pattern, the near-total absence of preceding clinical signs and "
                                    "why an unremarkable necropsy is itself informative, and diagnosis/prevention "
                                    "including distinct angles like disturbance-avoidance and real dark periods.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Almost no warning sign beforehand — unlike nearly everything else you'll diagnose",
                    "sales_subheadline": "3 modules on broiler sudden death syndrome — the arrhythmia mechanism, "
                                          "why an unremarkable necropsy matters, and distinct prevention angles.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving broiler operations\n"
                        "Practitioners investigating apparently healthy birds found dead with no preceding signs\n"
                        "Anyone who's taken the Ascites Syndrome course and wants the direct comparison"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Broiler sudden death syndrome CE for vets — arrhythmia mechanism, "
                                         "diagnosis by exclusion, and distinct prevention angles.",
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
                organization=org, name="Sudden Death Syndrome of Broiler Chickens — Final Exam",
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
                title="Final Exam — Sudden Death Syndrome of Broiler Chickens",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
