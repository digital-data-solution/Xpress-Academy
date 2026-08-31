from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# First of a mixed dogs/cats/livestock batch — back to the original
# ~30-topic mixed-species list after the dedicated 20-poultry sweep
# (see seed_mycoplasmosis_poultry_course.py for that batch's header,
# and seed_newcastle_disease_course.py for the original mixed-batch
# context). Same VET-audience single-topic CE micro-course shape,
# same Veterinary Continuing Education programme.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>A morbillivirus with a wide host range</h2>
<p>Canine distemper is caused by canine distemper virus (CDV), a morbillivirus — the same genus as measles virus and, on the veterinary side, peste des petits ruminants virus, already covered in its own course on this platform. Like both of those relatives, CDV is an enveloped RNA virus.</p>
<h2>Highly contagious, and not just a dog-to-dog risk</h2>
<p>Transmission is via aerosol and direct contact, and spread is highly contagious once introduced. CDV's host range extends well beyond dogs — ferrets, foxes, raccoons, and other wild carnivores can act as reservoirs, meaning wildlife contact is a real risk even for a well-managed, otherwise low-exposure kennel.</p>
<h2>The same vulnerable window as parvovirus</h2>
<p>Puppies are most vulnerable in the gap between waning maternal antibody and a completed vaccination series — the same epidemiological pattern already established for canine parvovirus, and worth remembering as a general principle across puppy diseases on this platform, not just this one.</p>"""),
    ("Clinical Findings",
     """<h2>A sequential, multisystem disease</h2>
<p>Distemper's clinical course is genuinely sequential, not a single fixed presentation: fever and respiratory signs (nasal and ocular discharge, coughing) come first, followed by GI signs (vomiting, diarrhea), which can then progress to NEUROLOGICAL signs — seizures, myoclonus, ataxia, paralysis.</p>
<h2>The delayed neurological threat</h2>
<p>Neurological signs can appear WEEKS after a dog seemed to have recovered from the earlier respiratory and GI phases, and when they do appear, they can be permanent. This delayed-onset pattern is one of the most important facts in this course — a dog that looks recovered isn't necessarily out of danger.</p>
<h2>Two lasting, visible markers</h2>
<p>Hyperkeratosis of the nose and footpads ("hard pad disease") appears in some cases. Enamel hypoplasia — a lifelong visible marker on the teeth — occurs in puppies infected before their permanent teeth erupt, sometimes the only lasting sign that a dog survived distemper as a puppy.</p>"""),
    ("Diagnosis",
     """<h2>Building the diagnosis</h2>
<p>Clinical signs and history are the starting point, particularly the sequential respiratory-then-GI-then-neurological pattern. PCR — on respiratory or conjunctival swabs, or blood — is the standard confirmatory test.</p>
<h2>Why antibody titers are less useful here</h2>
<p>Antibody titers are less useful for diagnosis given vaccine cross-reactivity — a vaccinated dog will show antibodies regardless of current infection status, so titers can't reliably distinguish past vaccination from active disease the way PCR can.</p>
<h2>Key differentials</h2>
<p>Parvovirus (given the GI overlap), the kennel cough complex (given the respiratory overlap), and other causes of neurological signs all need to be considered.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment — supportive, with a variable prognosis</h2>
<p>There is no antiviral treatment. Supportive care — fluids, nutrition, anti-seizure medication if needed, antibiotics for secondary infection — is the standard approach. Prognosis is variable and genuinely worse once neurological involvement appears, tying back to the delayed-onset risk covered in the clinical findings module.</p>
<h2>Control</h2>
<p>Isolation and disinfection are standard — CDV is enveloped, making it easier to inactivate than a non-enveloped virus like parvovirus, a real practical difference worth knowing when comparing outbreak response between the two diseases.</p>
<h2>Prevention — the standard puppy series</h2>
<p>Core vaccination via the standard puppy series through 16 weeks is highly effective prevention. Avoiding unvaccinated puppy exposure to wildlife or unknown dogs matters specifically because of the wide wildlife host range covered earlier.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment for an individual patient. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is it dangerous to assume a dog is fully recovered once its respiratory and GI signs from distemper resolve?",
        "Neurological signs can appear WEEKS after apparent recovery from the earlier phases, and when they do "
        "appear, they can be permanent — the disease's course is sequential, not finished after the first two phases.",
        "Neurological signs can emerge weeks later and can be permanent, even after earlier signs have resolved",
        "Once respiratory and GI signs resolve, a dog is reliably clear of any further distemper-related risk",
    ),
    (
        "Why does wildlife contact represent a real risk even for a well-managed kennel with no obvious dog-to-dog exposure?",
        "CDV's host range extends beyond dogs to ferrets, foxes, raccoons, and other wild carnivores, which can "
        "act as reservoirs regardless of how controlled the kennel's own dog population is.",
        "CDV's wide host range includes wild carnivores that can act as reservoirs independent of kennel management",
        "CDV only ever transmits between dogs, so wildlife contact carries no meaningful distemper risk",
    ),
    (
        "Why are antibody titers less useful than PCR for diagnosing active canine distemper?",
        "Vaccine cross-reactivity means a vaccinated dog will show antibodies regardless of current infection "
        "status, so titers can't reliably distinguish past vaccination from an active infection.",
        "Vaccine cross-reactivity means titers can't reliably separate past vaccination from a genuinely active infection",
        "Antibody titers are actually more reliable than PCR for diagnosing active distemper infection",
    ),
    (
        "Why is CDV generally easier to control through isolation and disinfection than canine parvovirus?",
        "CDV is enveloped, making it easier to inactivate with standard disinfectants than a non-enveloped, "
        "environmentally hardy virus like parvovirus.",
        "CDV is enveloped, making it easier to inactivate with standard disinfectants than parvovirus",
        "CDV and parvovirus are equally difficult to control through isolation and disinfection measures",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Canine Distemper' — first of a mixed dogs/cats/livestock batch "
        "following the dedicated 20-poultry sweep. Safe to re-run."
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
                organization=org, programme=programme, slug="canine-distemper",
                defaults={
                    "title": "Canine Distemper",
                    "subtitle": "A multisystem viral disease that can hit the gut, lungs, and nervous system in "
                                 "sequence — with neurological signs sometimes appearing weeks after apparent recovery.",
                    "description": "<p>A 4-module continuing-education course on canine distemper — etiology and "
                                    "the wide wildlife host range that makes this more than a dog-to-dog risk, the "
                                    "sequential multisystem clinical course and delayed neurological threat, "
                                    "diagnosis including why titers are less useful here, and treatment/control/"
                                    "prevention centered on the core puppy vaccination series.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "A dog that looks recovered isn't necessarily out of danger — know why",
                    "sales_subheadline": "4 modules on canine distemper — sequential organ involvement, the "
                                          "delayed neurological threat, diagnosis, and core vaccination prevention.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or emergency practice\n"
                        "Practitioners counseling clients on puppy vaccination timing and wildlife exposure risk\n"
                        "Anyone who's taken the Canine Parvovirus course and wants the related puppy-vulnerability pattern"
                    ),
                    "not_for": (
                        "Pet owners without veterinary training looking for basic care guidance — this is written "
                        "at clinical practice depth"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Canine distemper CE for vets — sequential organ involvement, delayed "
                                         "neuro signs, and core vaccination prevention.",
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
                organization=org, name="Canine Distemper — Final Exam",
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
                title="Final Exam — Canine Distemper",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
