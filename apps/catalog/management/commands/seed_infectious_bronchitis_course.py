from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Second of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A coronavirus with a strain-diversity problem</h2>
<p>Infectious bronchitis (IB) is one of the most contagious respiratory diseases of chickens, caused by infectious bronchitis virus — a coronavirus for which chickens are the only natural host. What makes it genuinely difficult to control isn't the virus's contagiousness alone, but strain diversity: numerous serotypes and variants circulate worldwide (Massachusetts, 4/91, QX, and various regional strains), and protection from one variant often gives partial or no protection against a different circulating variant.</p>
<h2>How fast and how far it spreads</h2>
<p>IB spreads extremely efficiently — airborne over real distances, plus direct contact and contaminated equipment or personnel. Morbidity approaches 100% within days of introduction to a susceptible flock. Mortality is usually low in adults but can be significant in young chicks infected with nephropathogenic strains.</p>
<h2>The hidden long-term cost</h2>
<p>Chicks infected under roughly two weeks of age can suffer permanent oviduct damage, becoming "false layers" that never reach normal production even after apparent clinical recovery — a cost that's easy to miss because the bird looks fine by the time anyone's counting eggs again.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>The typical respiratory picture</h2>
<p>Sudden respiratory signs — gasping, coughing, tracheal rales, nasal discharge — spreading through a flock within one to two days. In layers, a sharp egg production drop appears alongside poor-quality eggs (thin or soft shells, watery albumen) that can persist well past the acute phase.</p>
<h2>The nephropathogenic form</h2>
<p>Strains that target the kidney add depression, wet droppings, increased water consumption, and higher mortality in young birds specifically — a meaningfully different and more dangerous presentation than the classic respiratory form.</p>
<h2>What necropsy shows</h2>
<p>The respiratory form shows tracheal congestion, mucus, and mild airsacculitis. Nephropathogenic strains produce swollen, pale kidneys with urate deposits — "visceral gout." False layers show a cystic, non-functional oviduct at necropsy, the physical evidence behind the production loss described above.</p>"""),
    ("Diagnosis",
     """<h2>Recognizing the pattern</h2>
<p>Rapid spread, high morbidity, and the combination of respiratory signs with an egg production drop together form a recognizable pattern — though several other diseases can look similar early on.</p>
<h2>Why strain typing matters, not just detection</h2>
<p>RT-PCR is the standard for detection AND strain typing — and strain typing is critical here specifically because it determines which vaccine will actually work against what's circulating on a given farm. Virus isolation and paired serology are also used, particularly where strain typing needs confirmation.</p>
<h2>Key differentials</h2>
<p>Newcastle disease, avian influenza, infectious laryngotracheitis, and mycoplasmosis all need to be considered before settling on an IB diagnosis.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment — supportive, watch for secondary infection</h2>
<p>There is no antiviral treatment. Management is supportive care plus antibiotics for secondary bacterial infection — which is very common in IB cases and often determines how severe the outbreak actually turns out to be.</p>
<h2>Control</h2>
<p>Isolation and disinfection are the mainstay — IBV is enveloped and relatively easy to inactivate compared to a hardier virus like parvovirus, which is one piece of good news in an otherwise fast-moving disease.</p>
<h2>Prevention — where strain match is everything</h2>
<p>Vaccination is the backbone of prevention, but strain match matters enormously: a vaccination program should reflect the variants actually circulating locally, not a generic off-the-shelf schedule. Live vaccines are typically given early — often at the hatchery or in the first week — with inactivated boosters in layers and breeders. Biosecurity gaps are punished fast given how quickly IBV spreads once it's introduced.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment or a strain-specific vaccination protocol for a given farm. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why does infectious bronchitis remain difficult to control even with vaccination widely available?",
        "Numerous serotypes/variants circulate worldwide, and protection from one variant often gives partial or "
        "no protection against a different circulating variant — so strain match is the real control problem.",
        "Cross-protection between different circulating IBV strains is often incomplete",
        "The virus is impossible to inactivate with any standard disinfectant, unlike most enveloped viruses",
    ),
    (
        "Why are 'false layers' considered a hidden cost of an IB outbreak?",
        "Chicks infected under about two weeks of age can suffer permanent oviduct damage — they can look "
        "clinically recovered while never reaching normal egg production again.",
        "Chicks infected very young can suffer permanent oviduct damage despite appearing clinically recovered",
        "False layers are a rare, clinically obvious complication that's easy to catch and treat",
    ),
    (
        "Why does RT-PCR's ability to strain-type an IB outbreak matter beyond simple detection?",
        "Strain typing determines which vaccine will actually be effective against what's circulating on that farm "
        "— detection alone doesn't tell you whether the current vaccination program will actually work.",
        "It identifies which vaccine will actually protect against the specific strain currently circulating",
        "Strain typing has no practical bearing on vaccine choice once IB has already been detected",
    ),
    (
        "Why should an IB vaccination program be built around locally circulating strains rather than a generic schedule?",
        "Because protection is strain-specific and often incomplete across variants, a generic program can leave a "
        "flock exposed to whatever strain is actually circulating in that region.",
        "A generic vaccination schedule may not protect against the specific strains actually circulating locally",
        "Any IB vaccine gives equally strong protection against every circulating strain regardless of match",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Infectious Bronchitis in Chickens' — second of the poultry-only "
        "~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="infectious-bronchitis-in-chickens",
                defaults={
                    "title": "Infectious Bronchitis in Chickens",
                    "subtitle": "One of the most contagious poultry diseases — and one where strain match, not "
                                 "just vaccination, decides whether a program actually works.",
                    "description": "<p>A 4-module continuing-education course on infectious bronchitis — etiology "
                                    "and the strain-diversity problem that defines its control, clinical findings "
                                    "including the nephropathogenic form and false-layer cost, diagnosis with "
                                    "strain typing, and treatment/control/prevention centered on matching "
                                    "vaccination programs to local strains.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Near-100% morbidity in days — and a vaccine mismatch you might not know about",
                    "sales_subheadline": "4 modules on infectious bronchitis — the nephropathogenic form, false "
                                          "layers, and why strain typing decides your vaccination program.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners designing or reviewing a flock's vaccination program\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Infectious bronchitis CE for vets — strain diversity, diagnosis, and "
                                         "matching vaccination programs to local strains.",
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
                organization=org, name="Infectious Bronchitis in Chickens — Final Exam",
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
                title="Final Exam — Infectious Bronchitis in Chickens",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
