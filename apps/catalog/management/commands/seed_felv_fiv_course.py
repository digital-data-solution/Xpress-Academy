from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# First of a cat-coverage-gap-closing batch (Sam's own count: cats had
# only 3 posts vs dogs' 8 and poultry's 20 — 8 more brings cats to 11).
# Clinical VET-audience CE content, same Veterinary Continuing
# Education programme as the dog/livestock courses — explicitly NOT
# the "Pet Owner Education" track built for the prior general/
# cross-species batch (see seed_recognizing_vet_emergency_course.py
# for that track's own header and rationale).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Tested together, but genuinely different viruses</h2>
<p>Feline leukemia virus (FeLV) is a retrovirus causing bone marrow suppression, anemia, immunosuppression, and cancer — particularly lymphoma and leukemia. Feline immunodeficiency virus (FIV) is a lentivirus, in the same subfamily as HIV, causing progressive immune decline over years. Despite the name similarity to HIV, FIV is NOT transmissible to humans — worth stating plainly, since the name alone can cause unnecessary alarm.</p>
<h2>Two genuinely different transmission routes</h2>
<p>FeLV spreads via close, prolonged contact — mutual grooming, shared food bowls, bite wounds, and queen-to-kitten transmission in utero or through milk — requiring more sustained contact than a single altercation. FIV spreads primarily via DEEP BITE WOUNDS, which is why outdoor, unneutered male cats with a fighting history carry dramatically higher risk — a genuinely different exposure profile from FeLV, even though the two are routinely tested together.</p>"""),
    ("Clinical Findings",
     """<h2>Wide, nonspecific signs as immunosuppression progresses</h2>
<p>Both viruses cause wide, nonspecific signs as immunosuppression advances: recurrent infections, weight loss, a poor coat, chronic gingivitis or stomatitis (particularly associated with FIV), and enlarged lymph nodes.</p>
<h2>Different disease courses worth knowing separately</h2>
<p>FeLV specifically causes anemia, lymphoma, and increased susceptibility to infection, generally following a more aggressive course. FIV typically follows a slower course — many FIV-positive cats live years with good quality of life, particularly when kept indoors, a meaningfully different prognosis conversation from FeLV that's worth having explicitly with an owner rather than treating both diagnoses as equally grim.</p>"""),
    ("Diagnosis, Treatment, and Prevention",
     """<h2>Testing, and a real false-positive trap</h2>
<p>The point-of-care ELISA combo test is standard. A positive result in a healthy-looking kitten needs follow-up confirmation — false positives occur, and maternal antibody can cause a temporary false-positive FIV result in kittens that resolves as the maternal antibody wanes. PCR is used for genuinely ambiguous cases.</p>
<h2>No cure, but real management options</h2>
<p>There is no cure for either virus. Supportive care, prompt treatment of secondary infections, good nutrition, parasite control, and minimizing stress and further exposure form the core of management. Positive cats should be kept strictly indoors — this protects both the affected cat from additional infections and other cats from exposure.</p>
<h2>Prevention</h2>
<p>An FeLV vaccine exists and is recommended for cats with real outdoor or exposure risk. No widely available FIV vaccine exists in most markets. Testing new cats before introducing them to a household, and neutering males to reduce the fighting behavior that spreads FIV, are the practical prevention tools available.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why do FeLV and FIV carry genuinely different risk profiles despite routinely being tested together?",
        "FeLV spreads via close, prolonged contact like grooming and shared bowls, while FIV spreads mainly "
        "through deep bite wounds — meaning very different cats are actually at highest risk for each.",
        "FeLV needs sustained close contact, while FIV spreads mainly through deep bite wounds from fighting",
        "Both viruses spread through the exact same transmission routes and carry an identical risk profile",
    ),
    (
        "Why is it worth explicitly telling owners that FIV is not transmissible to humans?",
        "The name similarity to HIV can cause unnecessary alarm, even though FIV is a distinct lentivirus with no "
        "real transmission risk to people.",
        "The name's similarity to HIV can cause unnecessary alarm despite there being no real human transmission risk",
        "FIV can occasionally transmit to immunocompromised household members under specific circumstances",
    ),
    (
        "Why might a healthy-looking kitten test positive for FIV without actually being infected?",
        "Maternal antibody can cause a temporary false-positive FIV result in kittens, which resolves as the "
        "maternal antibody naturally wanes — a real reason to confirm with follow-up testing.",
        "Maternal antibody can cause a temporary false-positive result that resolves as the antibody wanes",
        "Kittens are biologically incapable of producing a false-positive result on the standard ELISA combo test",
    ),
    (
        "Why is FIV's typical prognosis conversation meaningfully different from FeLV's, worth having explicitly with an owner?",
        "FIV generally follows a slower course, with many FIV-positive cats living years with good quality of "
        "life indoors, while FeLV tends toward a more aggressive disease course.",
        "FIV generally follows a slower course with good long-term quality of life, unlike FeLV's more aggressive course",
        "Both viruses carry an identical prognosis and require the same conversation with an owner about outlook",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Feline Leukemia Virus (FeLV) and Feline Immunodeficiency Virus "
        "(FIV)' — first of the cat-coverage-gap-closing batch. Safe to re-run."
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
                organization=org, programme=programme, slug="felv-fiv-in-cats",
                defaults={
                    "title": "Feline Leukemia Virus (FeLV) and Feline Immunodeficiency Virus (FIV)",
                    "subtitle": "Tested together, but with genuinely different transmission routes — one "
                                 "spreads through casual close contact, the other mainly through bite wounds "
                                 "from fighting.",
                    "description": "<p>A 3-module continuing-education course on FeLV and FIV — etiology and "
                                    "their genuinely different transmission routes, clinical findings and the "
                                    "meaningfully different disease courses each follows, and diagnosis (including "
                                    "a real false-positive trap in kittens) plus treatment and prevention.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_published": False,
                    "sales_headline": "Tested together, but with genuinely different risk profiles worth knowing apart",
                    "sales_subheadline": "3 modules on FeLV and FIV — different transmission routes, disease "
                                          "courses, and a real false-positive trap in kitten testing.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general practice\n"
                        "Practitioners counseling owners on a new positive test result and realistic prognosis\n"
                        "Anyone advising shelters or multi-cat households on testing protocols"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "FeLV/FIV CE for vets — different transmission routes, disease courses, "
                                         "and a real false-positive trap in kittens.",
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
                organization=org, name="FeLV and FIV — Final Exam",
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
                title="Final Exam — FeLV and FIV",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
