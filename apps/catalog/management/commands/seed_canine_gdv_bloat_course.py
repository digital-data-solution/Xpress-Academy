from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifth of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("What's Actually Happening",
     """<h2>Hours matter, not days</h2>
<p>Gastric dilatation-volvulus (GDV), commonly called bloat, is one of the fastest-moving true emergencies in companion animal medicine. Unproductive retching plus a distended abdomen in a large or giant-breed dog demands immediate action — this is not a condition where waiting to see how things develop is a safe option.</p>
<h2>Dilatation, then volvulus</h2>
<p>The stomach fills with gas (dilatation) and, in the severe classic presentation, twists on its own axis (volvulus). This twisting cuts off blood supply to the stomach and spleen, and rapidly compresses the major vessels returning blood to the heart — which is exactly why progression to shock happens so extremely fast, faster than almost any other condition on this platform.</p>"""),
    ("Risk Factors and Clinical Findings",
     """<h2>Who's at highest risk</h2>
<p>Large and giant, deep-narrow-chested breeds are dramatically overrepresented, though GDV can occur in any dog. Eating rapidly, feeding one large daily meal instead of split meals, exercising near mealtime, and family history are all associated risk factors — but no single factor reliably predicts which individual dog will actually develop GDV.</p>
<h2>The key distinguishing sign</h2>
<p>UNPRODUCTIVE retching — bringing up little or nothing — is the key sign that distinguishes GDV from ordinary vomiting, and is often the first thing an owner notices. A visibly distended abdomen, restlessness and distress, and rapid breathing follow. Without prompt intervention, this progresses to weakness, collapse, and shock signs — pale gums, a rapid weak pulse.</p>"""),
    ("Diagnosis and Treatment",
     """<h2>Confirming, without delaying care</h2>
<p>Clinical signs combined with an abdominal radiograph confirm the diagnosis — the radiograph shows the twisted-stomach appearance and distinguishes simple dilatation from true volvulus. But this confirmation should NEVER delay getting the dog to a vet immediately; the workup happens in parallel with emergency care, not before it.</p>
<h2>Surgery is the treatment</h2>
<p>GDV is a surgical emergency. Stabilization — IV fluids for shock, stomach decompression — comes first, followed by surgery to untwist the stomach PLUS gastropexy: surgically attaching the stomach to the body wall to prevent recurrence. Without gastropexy, there's a high risk of the same episode happening again. Tissue that's been compromised by the loss of blood supply may need to be removed during the same surgery.</p>"""),
    ("Prevention",
     """<h2>A real proactive option, not just a post-scare conversation</h2>
<p>Elective prophylactic gastropexy is a genuine option for high-risk breeds, sometimes performed alongside routine spay or neuter — worth raising as a proactive conversation for giant-breed puppies specifically, not only after a dog has already had a frightening episode.</p>
<h2>Lower-certainty risk-reduction measures</h2>
<p>Multiple smaller meals instead of one large one, avoiding exercise right before or after eating, and slow-feed bowls are all lower-certainty risk-reduction measures — reasonable to recommend, but genuinely less proven than prophylactic gastropexy for a dog whose breed puts it at real risk.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment during a real emergency. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is unproductive retching considered the key distinguishing sign of GDV rather than ordinary vomiting?",
        "It brings up little or nothing, distinguishing it clinically from ordinary vomiting — and is often the "
        "first thing an owner actually notices before other signs appear.",
        "It brings up little or nothing, unlike ordinary vomiting, and is often the earliest noticeable sign",
        "Unproductive retching is clinically identical to ordinary vomiting and carries no diagnostic significance",
    ),
    (
        "Why does GDV progress to shock so much faster than most other emergency conditions?",
        "The twisted stomach rapidly compresses the major vessels returning blood to the heart, on top of cutting "
        "off blood supply to the stomach and spleen — a mechanism that accelerates shock unusually quickly.",
        "The twisted stomach rapidly compresses major vessels returning blood to the heart, accelerating shock",
        "GDV's progression to shock actually occurs at a similar pace to most other abdominal emergencies",
    ),
    (
        "Why is gastropexy performed alongside untwisting the stomach during GDV surgery, rather than untwisting alone?",
        "Without gastropexy, there's a high risk of the same volvulus happening again — gastropexy is what "
        "specifically prevents recurrence, not just resolves the immediate emergency.",
        "Untwisting alone leaves a high risk of the same volvulus recurring without the added gastropexy",
        "Gastropexy is purely a precautionary step with no real effect on the likelihood of recurrence",
    ),
    (
        "Why is prophylactic gastropexy worth raising proactively with owners of high-risk breeds, rather than only after a scare?",
        "It's a real, genuine preventive option for breeds at dramatically elevated risk, and can be performed "
        "alongside a routine procedure like spay or neuter rather than as an emergency response later.",
        "It's a genuine preventive option for high-risk breeds that can be done alongside a routine procedure",
        "Prophylactic gastropexy is not a real option and should only ever be considered after a first episode",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Gastric Dilatation-Volvulus (Bloat): Emergency Recognition' — fifth "
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
                organization=org, programme=programme, slug="gastric-dilatation-volvulus-bloat",
                defaults={
                    "title": "Gastric Dilatation-Volvulus (Bloat): Emergency Recognition",
                    "subtitle": "Hours matter, not days. Unproductive retching plus a distended abdomen in a "
                                 "large or giant-breed dog is one of the fastest-moving true emergencies in "
                                 "companion animal medicine.",
                    "description": "<p>A 4-module continuing-education course on GDV (bloat) — the dilatation-"
                                    "then-volvulus mechanism and why shock progresses so fast, risk factors and "
                                    "the key unproductive-retching sign, diagnosis and emergency surgery including "
                                    "gastropexy, and prophylactic prevention for high-risk breeds.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "One of the fastest-moving true emergencies in companion animal medicine",
                    "sales_subheadline": "4 modules on GDV (bloat) — recognition, emergency surgery and "
                                          "gastropexy, and the proactive prevention conversation for high-risk breeds.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or emergency practice\n"
                        "Practitioners advising owners of large/giant deep-chested breeds\n"
                        "Anyone wanting a clear framework for recognizing and responding to this emergency fast"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "GDV (bloat) CE for vets — emergency recognition, surgery and gastropexy, "
                                         "and prophylactic prevention for high-risk breeds.",
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
                organization=org, name="GDV (Bloat) — Final Exam",
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
                title="Final Exam — Gastric Dilatation-Volvulus (Bloat)",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
