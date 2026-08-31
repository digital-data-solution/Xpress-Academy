from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Third of the mixed dogs/cats/livestock batch (see
# seed_canine_distemper_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A parasite that spreads only one way</h2>
<p>Heartworm in dogs is caused by Dirofilaria immitis, a parasitic roundworm transmitted ONLY by mosquito bite — there is no direct dog-to-dog transmission. Adult worms live in the heart and pulmonary arteries, which is exactly why advanced disease presents as cardiac and respiratory signs.</p>
<h2>Why proximity to other dogs isn't the risk factor</h2>
<p>Risk correlates directly with mosquito exposure and density — climate, standing water, and season all matter. A dog's heartworm risk has nothing to do with other dogs it encounters, which is a genuinely important distinction to make clearly for owners who assume risk works the same way as a contagious disease like parvovirus or distemper.</p>"""),
    ("Clinical Findings",
     """<h2>Often silent early on</h2>
<p>Early infection is often subclinical, with no signs an owner or even a routine exam would necessarily catch.</p>
<h2>Progressive disease</h2>
<p>As disease progresses: a mild, persistent cough, reduced exercise tolerance, and appetite or weight loss appear. Advanced disease produces heart failure signs — labored breathing, abdominal fluid from right heart failure.</p>
<h2>Caval syndrome — a true emergency</h2>
<p>In severe cases, "caval syndrome" can occur — a sudden, life-threatening blood-flow blockage requiring emergency surgical worm removal. This represents the far end of a disease that, in its earlier stages, can be entirely silent — underscoring why screening matters more than waiting for obvious signs.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>Screening — and its real limits</h2>
<p>The antigen blood test, detecting adult female worms, is the standard annual screening tool. It can be falsely negative early in infection or in light or male-only infections, so a negative test isn't an absolute guarantee, particularly in a dog with a suspicious clinical picture. Microscopic examination for circulating microfilariae supplements the antigen test.</p>
<h2>Treatment — genuinely involved, and risky if rushed</h2>
<p>A specific adulticide protocol exists but is genuinely involved: staged over weeks, with STRICT exercise restriction throughout, since dead or dying worms can cause dangerous clots if the dog is active during treatment. This real risk is exactly why prevention is emphasized so heavily over treatment throughout this course — treatment works, but it's a genuinely more difficult and riskier path than avoiding infection in the first place.</p>
<h2>Why there's no environmental control equivalent</h2>
<p>Unlike tick- or mite-vectored diseases covered elsewhere on this platform, there's no environmental control measure for heartworm — it's mosquito-vectored, not something that lives in bedding or housing cracks the way a tick or mite does.</p>
<h2>Prevention — the real answer</h2>
<p>Monthly preventive medication is highly effective, and is recommended YEAR-ROUND in mosquito-endemic climates, not just seasonally — a genuinely important distinction for a Nigerian climate where mosquito exposure doesn't have the sharp seasonal drop-off some other climates see.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is a dog's proximity to other dogs not a meaningful heartworm risk factor?",
        "Dirofilaria immitis transmits ONLY by mosquito bite, with no direct dog-to-dog transmission — risk tracks "
        "mosquito exposure specifically, not contact with other dogs.",
        "Transmission occurs only via mosquito bite, so risk tracks mosquito exposure rather than dog-to-dog contact",
        "Heartworm spreads primarily through direct contact between dogs, similar to many other canine diseases",
    ),
    (
        "Why can the standard antigen blood test give a false negative in some real cases?",
        "It detects adult female worms specifically, so it can be falsely negative early in infection or in light "
        "or male-only infections — a real limitation worth remembering when a clinical picture still looks suspicious.",
        "It detects adult female worms specifically, which can miss early, light, or male-only infections",
        "The antigen blood test is fully reliable in every stage and type of heartworm infection",
    ),
    (
        "Why is strict exercise restriction required during heartworm adulticide treatment?",
        "Dead or dying worms can cause dangerous blood clots if the dog is active during treatment — the "
        "restriction directly reduces that real, treatment-related risk.",
        "Dead or dying worms can cause dangerous clots if the treated dog remains physically active",
        "Exercise restriction during treatment is a precaution with no real physiological basis",
    ),
    (
        "Why is year-round heartworm prevention recommended in mosquito-endemic climates rather than seasonal prevention?",
        "These climates don't have the sharp seasonal drop-off in mosquito activity that some other regions see, "
        "so mosquito exposure — and therefore heartworm risk — persists throughout the year.",
        "Mosquito exposure persists throughout the year in these climates without a sharp seasonal drop-off",
        "Heartworm risk is identical year-round in every climate, making seasonal timing irrelevant everywhere",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Heartworm and Mosquito-Borne Parasites in Dogs' — third of the mixed "
        "dogs/cats/livestock batch. Safe to re-run."
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
                organization=org, programme=programme, slug="heartworm-mosquito-borne-parasites-dogs",
                defaults={
                    "title": "Heartworm and Mosquito-Borne Parasites in Dogs",
                    "subtitle": "Spread only by mosquito bite, not dog-to-dog contact — proximity to other dogs "
                                 "isn't the risk factor, mosquito exposure is.",
                    "description": "<p>A 3-module continuing-education course on canine heartworm — etiology and "
                                    "the mosquito-only transmission that redefines what 'risk' actually means "
                                    "here, clinical progression from silent infection to caval syndrome, and "
                                    "diagnosis/treatment/prevention centered on why year-round monthly prevention "
                                    "beats the genuinely risky treatment protocol.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Proximity to other dogs has nothing to do with this one's risk factor",
                    "sales_subheadline": "3 modules on canine heartworm — mosquito-only transmission, disease "
                                          "progression, and why year-round prevention beats risky treatment.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners counseling clients on year-round versus seasonal prevention\n"
                        "Anyone advising on annual screening protocols for dogs in mosquito-endemic areas"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Canine heartworm CE for vets — mosquito-only transmission, disease "
                                         "progression, and year-round prevention versus treatment risk.",
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
                organization=org, name="Heartworm and Mosquito-Borne Parasites in Dogs — Final Exam",
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
                title="Final Exam — Heartworm and Mosquito-Borne Parasites in Dogs",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
