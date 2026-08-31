from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Seventh of the cat-coverage-gap-closing batch (see
# seed_felv_fiv_course.py's header for the batch's overall context).
# Explicitly cross-references seed_felv_fiv_course.py — same
# underlying behavior (unneutered male fighting) drives both bite
# abscess risk and FIV transmission risk, matching how the source
# article itself framed the connection.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A wound that seals while the real problem develops underneath</h2>
<p>Cat bite abscesses form from cat-on-cat bites — typically territorial fighting among outdoor, unneutered, or free-roaming cats — which deposit mouth bacteria deep under the skin. A cat's sharp, narrow teeth create a small entry wound that closes over quickly. WOUND SEALS AT THE SURFACE WHILE BACTERIA MULTIPLY UNDERNEATH, forming an abscess over the following days. This is one of the most frequent reasons an outdoor cat ends up seeing a vet.</p>
<h2>Who's actually at risk</h2>
<p>Unneutered male cats with outdoor access are dramatically overrepresented — the SAME risk factor already established for FIV transmission in its own course on this platform, genuinely the same underlying territorial and fighting behavior driving both conditions, not a coincidental overlap.</p>"""),
    ("Clinical Findings",
     """<h2>A delayed presentation, not an immediate one</h2>
<p>A firm, painful swelling develops over two to four days after an often-unwitnessed fight — commonly at the face, limbs, or tail base, the typical locations for a fight bite. Fever, lethargy, and reduced appetite frequently accompany the swelling as it develops.</p>
<h2>What happens if it isn't caught</h2>
<p>The abscess may rupture on its own, draining thick, foul-smelling pus — often with visible relief for the cat once it does, though this isn't a substitute for proper veterinary drainage and treatment.</p>"""),
    ("Diagnosis and Treatment",
     """<h2>Usually a straightforward clinical diagnosis</h2>
<p>Diagnosis is usually straightforward from the characteristic swelling combined with a plausible history — outdoor access, and sometimes a visible puncture wound or scab. Imaging is rarely needed unless the presentation is atypical.</p>
<h2>Draining is the essential step</h2>
<p>DRAINING is the essential step — either a vet lancing the abscess under sedation, or cleaning and flushing it if it's already ruptured on its own. Antibiotics alone, without addressing the pocket of infection directly, often aren't sufficient on their own. Antibiotics are given alongside drainage, together with pain management. Most cats fully recover within one to two weeks of proper treatment.</p>"""),
    ("Prevention",
     """<h2>The most effective single measure</h2>
<p>Indoor-only living, or supervised/enclosed outdoor access, is the most effective preventive measure, given the direct link to fighting behavior already established.</p>
<h2>Neutering — a real dual benefit</h2>
<p>NEUTERING MALE CATS significantly reduces territorial fighting and roaming, which reduces bite-abscess risk AND FIV transmission risk simultaneously — the same underlying behavior change addresses both problems at once, worth explicitly mentioning to an owner deciding whether neutering is worth it, since the benefit isn't limited to just one of these two conditions.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does a cat bite wound often seal at the surface while a serious infection develops underneath?",
        "A cat's sharp, narrow teeth create a small entry wound that closes over quickly, sealing bacteria "
        "deposited deep under the skin where it can multiply undetected until an abscess forms.",
        "Sharp, narrow teeth create a small entry wound that seals quickly, trapping bacteria to multiply underneath",
        "Cat bite wounds never seal at the surface, making the underlying infection immediately visible",
    ),
    (
        "Why are unneutered male cats with outdoor access dramatically overrepresented in both bite abscess and FIV cases?",
        "The same underlying territorial fighting behavior drives risk for both conditions — it isn't a "
        "coincidental overlap, but a shared root cause worth addressing together.",
        "The same underlying territorial fighting behavior drives elevated risk for both conditions at once",
        "Bite abscesses and FIV share no real underlying connection despite affecting a similar population",
    ),
    (
        "Why is draining a cat bite abscess considered essential, rather than treating with antibiotics alone?",
        "Antibiotics alone, without addressing the actual pocket of infection directly, often aren't sufficient "
        "on their own — the physical infection site needs to be opened and cleared, not just medicated.",
        "Antibiotics alone often aren't sufficient without directly addressing the infected pocket itself",
        "Antibiotics alone are typically fully sufficient to resolve a cat bite abscess without any drainage",
    ),
    (
        "Why does neutering a male cat address two separate risks (bite abscesses and FIV transmission) at once?",
        "Both risks stem from the same territorial fighting and roaming behavior, so reducing that behavior "
        "through neutering lowers risk for both conditions simultaneously, not just one or the other.",
        "Both risks stem from the same fighting/roaming behavior, so reducing it lowers risk for both together",
        "Neutering only meaningfully reduces bite abscess risk and has no real effect on FIV transmission risk",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Cat Bite Abscesses' — seventh of the cat-coverage-gap-closing "
        "batch. Safe to re-run."
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
                organization=org, programme=programme, slug="cat-bite-abscesses",
                defaults={
                    "title": "Cat Bite Abscesses",
                    "subtitle": "A cat's sharp teeth seal the surface wound shut fast — while the infection they "
                                 "deposited underneath keeps building until it becomes a genuine abscess days later.",
                    "description": "<p>A 4-module continuing-education course on cat bite abscesses — etiology "
                                    "and why unneutered male cats share the exact risk profile already "
                                    "established for FIV, the delayed clinical presentation, diagnosis and why "
                                    "drainage (not antibiotics alone) is essential, and prevention including "
                                    "neutering's dual benefit.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "The surface heals fast — while the real infection builds underneath",
                    "sales_subheadline": "4 modules on cat bite abscesses — the sealed-wound mechanism, why "
                                          "drainage matters most, and neutering's dual benefit alongside FIV risk.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners seeing outdoor male cats presenting with fresh swelling\n"
                        "Anyone who's taken the FeLV/FIV course and wants the connected behavioral risk factor"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Cat bite abscess CE for vets — sealed-wound mechanism, drainage-first "
                                         "treatment, and neutering's dual FIV/abscess benefit.",
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
                organization=org, name="Cat Bite Abscesses — Final Exam",
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
                title="Final Exam — Cat Bite Abscesses",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
