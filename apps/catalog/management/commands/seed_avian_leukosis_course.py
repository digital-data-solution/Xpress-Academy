from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Ninth of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context). Written
# deliberately alongside seed_mareks_disease_course.py's own content
# — this course leans on the reader already knowing that course, and
# repeatedly contrasts against it (bursal enlargement vs. atrophy,
# B-cell vs. T-cell, no vaccine vs. vaccine), matching how the article
# itself was framed. Best value if Marek's is seeded first, though
# each course stands alone.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A tumor-causing retrovirus, controlled almost the opposite way from Marek's</h2>
<p>Avian leukosis is caused by avian leukosis virus (ALV), a retrovirus with subgroups A through J — subgroup A/B commonly causes lymphoid leukosis, the most frequently encountered form. On the surface this looks similar to Marek's disease, another tumor-causing poultry virus — but the two are controlled in almost opposite ways, for a reason rooted entirely in how each one spreads.</p>
<h2>The single most important practical fact</h2>
<p>Transmission is predominantly VERTICAL — hen to chick via the egg — unlike Marek's airborne/dander route. Horizontal contact plays a lesser role. Infection is persistent and lifelong once it happens. This one epidemiological difference is what makes breeder-flock control genuinely effective for avian leukosis in a way it simply isn't for Marek's disease.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>Often silent for a long time</h2>
<p>Avian leukosis is often subclinical long-term. When lymphoid leukosis does present, it produces tumors in the bursa, liver, and spleen, along with depression, weight loss, and a pale comb — typically in birds over 16 weeks of age, sometimes ending in sudden death. Other, less common forms include erythroblastosis, myeloblastosis, and osteopetrosis.</p>
<h2>The key differentiator from Marek's disease</h2>
<p>Tumors are smooth and glistening. Critically, the bursa is typically ENLARGED in avian leukosis — the opposite of the bursal atrophy seen in Marek's disease. If you remember one visual differentiator between these two tumor-causing poultry viruses, this is it.</p>"""),
    ("Diagnosis",
     """<h2>Histopathology is definitive against Marek's disease</h2>
<p>Histopathology distinguishes avian leukosis from Marek's disease reliably: avian leukosis shows a B-cell, uniform pattern, while Marek's disease shows a T-cell, pleomorphic pattern — the exact mirror-image comparison covered from the Marek's side in that course. Combined with the bursal enlargement-versus-atrophy difference from the previous module, these two findings together should resolve most cases that look ambiguous on gross exam alone.</p>
<h2>Screening tools</h2>
<p>ELISA and PCR are used for breeder-flock screening — the practical entry point into the control strategy covered in the next module.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>No treatment, and no vaccine — a genuinely different situation from Marek's</h2>
<p>There is no treatment; cull affected birds. Unlike Marek's disease, no widespread vaccine exists for avian leukosis. This isn't an oversight in vaccine development — it's a direct consequence of how the virus behaves, covered next.</p>
<h2>Why breeder-flock eradication actually works here</h2>
<p>Because transmission is predominantly vertical, breeder-flock eradication through testing — ELISA on eggs or cloacal swabs, removing identified shedders — is genuinely effective at reducing disease going forward, in a way that simply isn't available for Marek's disease given its airborne/dander transmission route. Control here relies entirely on breeder testing and eradication, not on protecting individual chicks after the fact.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does breeder-flock eradication work as a real control strategy for avian leukosis but not for Marek's disease?",
        "Avian leukosis transmits predominantly vertically (hen to chick via the egg), so removing infected "
        "breeders directly reduces future disease — Marek's spreads mainly via airborne dander, which breeder "
        "testing alone can't interrupt.",
        "Avian leukosis spreads predominantly vertically, so removing infected breeders directly reduces future disease",
        "Breeder-flock eradication is equally effective against both diseases regardless of how each one spreads",
    ),
    (
        "What is the key gross lesion difference between avian leukosis and Marek's disease in the bursa?",
        "Avian leukosis typically shows bursal ENLARGEMENT, the opposite of the bursal atrophy typically seen in "
        "Marek's disease — a useful visual differentiator between the two.",
        "Avian leukosis shows bursal enlargement, while Marek's disease shows bursal atrophy",
        "Both diseases produce identical bursal changes, so the bursa isn't a useful differentiator between them",
    ),
    (
        "Why is there no widespread vaccine for avian leukosis, unlike Marek's disease?",
        "This follows from the same vertical-transmission biology that makes breeder eradication effective — the "
        "practical control strategy that actually works is testing and removing infected breeders, not vaccination.",
        "The predominantly vertical transmission route makes breeder testing and eradication the effective strategy instead",
        "A vaccine exists but is rarely used in practice because breeder eradication is simpler",
    ),
    (
        "How does histopathology distinguish avian leukosis from Marek's disease?",
        "Avian leukosis shows a B-cell, uniform pattern, while Marek's disease shows a T-cell, pleomorphic pattern "
        "— the two conditions differ reliably at this cellular level even when gross findings look similar.",
        "Avian leukosis shows a B-cell, uniform pattern; Marek's disease shows a T-cell, pleomorphic pattern",
        "Histopathology cannot reliably distinguish the two conditions from one another",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Avian Leukosis in Poultry' — ninth of the poultry-only ~20-topic "
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
                organization=org, programme=programme, slug="avian-leukosis-in-poultry",
                defaults={
                    "title": "Avian Leukosis in Poultry",
                    "subtitle": "A tumor-causing retrovirus that looks like Marek's disease on the surface — but "
                                 "is controlled almost the opposite way.",
                    "description": "<p>A 4-module continuing-education course on avian leukosis — etiology and "
                                    "the predominantly vertical transmission that defines its control strategy, "
                                    "clinical findings and the key bursal differentiator from Marek's disease, "
                                    "histopathology-based diagnosis, and why breeder-flock testing and eradication "
                                    "(not vaccination) is the real prevention strategy here.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Looks like Marek's disease on the surface — controlled the opposite way",
                    "sales_subheadline": "4 modules on avian leukosis — vertical transmission, the bursal "
                                          "differentiator, and why breeder eradication replaces vaccination here.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners distinguishing avian leukosis from Marek's disease in the field\n"
                        "Anyone who's taken the Marek's Disease course and wants the direct comparison"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Avian leukosis CE for vets — vertical transmission, diagnosis vs. "
                                         "Marek's, and breeder-flock eradication strategy.",
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
                organization=org, name="Avian Leukosis in Poultry — Final Exam",
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
                title="Final Exam — Avian Leukosis in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
