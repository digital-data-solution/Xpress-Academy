from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Second of the cat-coverage-gap-closing batch (see
# seed_felv_fiv_course.py's header for context). Explicitly
# cross-references the earlier "male cat straining, little output"
# scenario from seed_recognizing_vet_emergency_course.py — same
# underlying condition, this time at clinical CE depth.

MODULES = [
    ("An Umbrella Term, Not One Disease",
     """<h2>Four genuinely different causes under one label</h2>
<p>Feline lower urinary tract disease (FLUTD) is an umbrella term, not one disease. Under that umbrella: bladder stones (uroliths), urethral plugs, bacterial infection — actually uncommon in younger cats without other risk factors, despite the common assumption that a urinary problem must mean infection — and idiopathic cystitis, where no identifiable cause is found, is stress-linked, and is the MOST COMMON cause in younger cats specifically.</p>
<h2>Why anatomy changes the stakes completely</h2>
<p>MALE CATS face dramatically higher complete-blockage risk than females, due to a longer, narrower urethra. The same underlying condition is merely uncomfortable in a female cat and potentially life-threatening in a male — anatomy alone changes the stakes, not the underlying disease process itself. General risk factors across sexes include obesity, a sedentary indoor lifestyle, low water intake (particularly with a dry-food-only diet), multi-cat stress, and litter box issues.</p>"""),
    ("Clinical Findings — Including the True Emergency",
     """<h2>General FLUTD signs</h2>
<p>Straining, frequent attempts to urinate with little output, blood in the urine, urinating outside the litter box, excessive genital licking, and vocalizing from pain are the common signs across causes.</p>
<h2>The blocked cat — a true emergency</h2>
<p>A blocked cat shows a hard, painful, distended bladder, lethargy, vomiting, and collapse as toxins build up in the bloodstream — exactly the "male cat straining, little output" scenario already flagged as a true emergency in this platform's own Emergency Recognition course. Recognizing this specific pattern quickly is genuinely life-saving.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>Building the diagnosis</h2>
<p>Physical exam (palpating for a distended bladder), urinalysis, and imaging — X-ray or ultrasound — for stones or structural causes together build the diagnosis. Bloodwork in a suspected blockage checks for metabolic derangement, particularly elevated potassium and kidney values, which is exactly what makes a blockage genuinely life-threatening rather than merely uncomfortable.</p>
<h2>A blocked cat needs emergency intervention — always</h2>
<p>A blocked cat needs EMERGENCY intervention: sedation, catheterization, IV fluids, and correcting the metabolic derangement covered above. This is never manageable at home, under any circumstances — worth stating unambiguously given how quickly a blockage can become fatal.</p>
<h2>Managing non-blocked FLUTD, and prevention</h2>
<p>Non-blocked FLUTD is managed with dietary changes (therapeutic urinary diets, increasing water intake), pain management, stress reduction specifically for idiopathic cystitis, and surgery for certain stones or recurrent cases. For prevention: increasing water intake — wet food, water fountains, multiple water stations — is one of the most consistently useful measures across essentially every FLUTD cause. The standard litter box guideline is one box per cat plus one extra. Reducing multi-cat stress, maintaining a healthy weight, and a vet-prescribed therapeutic diet for a cat with a stone history round out real prevention.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment, especially in a suspected blockage. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is FLUTD described as an umbrella term rather than a single disease?",
        "It covers several genuinely different causes — bladder stones, urethral plugs, infection, and "
        "idiopathic cystitis — each with its own likelihood and management approach, not one uniform condition.",
        "It covers several genuinely different underlying causes, each requiring its own diagnostic and management approach",
        "FLUTD refers to a single, well-defined disease process with one consistent underlying cause",
    ),
    (
        "Why does the same underlying FLUTD condition carry dramatically different stakes in male versus female cats?",
        "Male cats have a longer, narrower urethra, making complete blockage far more likely — the anatomy, not "
        "the underlying disease process itself, is what changes the risk of a life-threatening outcome.",
        "Male cats' longer, narrower urethra makes complete blockage far more likely than in female cats",
        "Male and female cats face an identical level of risk from any given FLUTD cause",
    ),
    (
        "Why does a suspected blocked cat need bloodwork specifically checking potassium and kidney values?",
        "It checks for the metabolic derangement that makes a blockage genuinely life-threatening, not just "
        "uncomfortable — this is what distinguishes an emergency from a routine urinary complaint.",
        "It checks for metabolic derangement, which is exactly what makes a blockage life-threatening rather than just uncomfortable",
        "This bloodwork is a routine formality with no real bearing on how urgently the blockage needs treatment",
    ),
    (
        "Why is bacterial infection often a less likely explanation than assumed for a young cat's urinary symptoms?",
        "Bacterial infection is actually uncommon in younger cats without other risk factors — idiopathic "
        "cystitis is the most common cause in this age group, despite infection being the common first assumption.",
        "Infection is uncommon in younger cats without other risk factors, unlike idiopathic cystitis, which is more common",
        "Bacterial infection is actually the single most common cause of FLUTD symptoms in cats of any age",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Lower Urinary Tract Disease and Urinary Blockage' — second "
        "of the cat-coverage-gap-closing batch. Safe to re-run."
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
                organization=org, programme=programme, slug="feline-flutd-urinary-blockage",
                defaults={
                    "title": "Feline Lower Urinary Tract Disease and Urinary Blockage",
                    "subtitle": "The same underlying condition is uncomfortable in a female cat and potentially "
                                 "fatal in a male — anatomy alone changes the stakes completely.",
                    "description": "<p>A 3-module continuing-education course on FLUTD — the umbrella of "
                                    "genuinely different causes and why idiopathic cystitis, not infection, "
                                    "dominates in young cats, clinical findings including the true-emergency "
                                    "blocked-cat presentation, and diagnosis/treatment/prevention centered on why "
                                    "a blockage always needs emergency intervention.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Same condition, wildly different stakes — anatomy alone decides which",
                    "sales_subheadline": "3 modules on FLUTD — the umbrella of real causes, the true-emergency "
                                          "blocked-cat presentation, and prevention that works across causes.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or emergency practice\n"
                        "Practitioners triaging a male cat presenting with straining and little urine output\n"
                        "Anyone who's taken the Recognizing a Veterinary Emergency guide and wants the clinical depth"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Feline FLUTD CE for vets — real causes, the true-emergency blocked-cat "
                                         "presentation, and cross-cause prevention.",
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
                organization=org, name="Feline FLUTD and Urinary Blockage — Final Exam",
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
                title="Final Exam — Feline FLUTD and Urinary Blockage",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
